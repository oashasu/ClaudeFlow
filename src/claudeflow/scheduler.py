"""流程调度模块 - 任务流程调度

V1核心功能：员工分配、阶段推进、失败处理、重试调度
V2新增功能：Session生命周期管理
V2.1.0新增功能：子任务检测、自然边界阻断、总结prompt注入、质量检查分支
"""

import uuid
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from claudeflow.state_machine import (
    TaskStatus, Phase, StateMachine,
    is_retriable, get_retry_interval
)
from claudeflow.task_manager import TaskManager
from claudeflow.subtask_detector import SubtaskDetector, CompletionType


# V2.1.0：阶段总结prompt模板（包含快速质量检查）
SUMMARY_PROMPT_TEMPLATE = """
子任务已完成，请总结本阶段工作（200字以内）：

- 关键决策：...
- 产出文件：...
- 遇到的问题及解决方案：...

自评质量（1-10分）：__
是否有疑虑需人工确认？（是/否）：__

完成总结后输出 # SUMMARY_COMPLETE
"""


class Scheduler:
    """流程调度器"""

    def __init__(self, task_manager: TaskManager):
        """
        初始化调度器

        Args:
            task_manager: 任务管理器实例
        """
        self.task_manager = task_manager
        self._task_contexts: Dict[str, Dict[str, Any]] = {}
        self._employee_status: Dict[str, str] = {}  # employee_id -> status
        # V2新增：Session生命周期管理
        self._sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session_info
        self._task_sessions: Dict[str, str] = {}  # task_id -> session_id
        # V2.1.0新增：子任务检测器
        self._subtask_detector = SubtaskDetector()

    def _init_task_context(self, task_id: str):
        """初始化任务上下文"""
        if task_id not in self._task_contexts:
            self._task_contexts[task_id] = {
                "retry_count": 0,
                "current_phase": Phase.REQUIREMENTS.value,
                "last_error_type": None,
                "last_error_message": None,
                "phase_history": [],
            }

    def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """获取任务上下文"""
        self._init_task_context(task_id)
        return self._task_contexts[task_id]

    def assign_employee(self, task_id: str, employee_id: str):
        """
        分配员工到任务

        Args:
            task_id: 任务ID
            employee_id: 员工ID
        """
        task = self.task_manager.get_task(task_id)

        # 更新任务状态为执行中
        self.task_manager.update_task(
            task_id,
            status=TaskStatus.RUNNING,
            assigned_employee=employee_id
        )

        # 标记员工为忙碌
        self._employee_status[employee_id] = "busy"

        # 初始化任务上下文
        self._init_task_context(task_id)

    def is_employee_available(self, employee_id: str) -> bool:
        """检查员工是否可用"""
        status = self._employee_status.get(employee_id, "idle")
        return status == "idle"

    def release_employee(self, employee_id: str):
        """释放员工"""
        self._employee_status[employee_id] = "idle"

    def get_current_phase(self, task_id: str) -> Phase:
        """获取当前阶段"""
        ctx = self.get_task_context(task_id)
        return Phase(ctx["current_phase"])

    def advance_phase(self, task_id: str):
        """
        推进到下一阶段

        Args:
            task_id: 任务ID
        """
        ctx = self.get_task_context(task_id)
        current_phase = Phase(ctx["current_phase"])

        # 记录阶段历史
        ctx["phase_history"].append({
            "phase": current_phase.value,
            "completed_at": datetime.now().isoformat()
        })

        # 推进到下一阶段
        if current_phase.value < Phase.ACCEPTANCE.value:
            next_phase = Phase(current_phase.value + 1)
            ctx["current_phase"] = next_phase.value

    def get_progress(self, task_id: str) -> int:
        """获取任务进度百分比"""
        ctx = self.get_task_context(task_id)
        current_phase = ctx["current_phase"]
        # 8个阶段，进度 = (当前阶段 - 1) / 8 * 100
        progress = int((current_phase - 1) * 100 / 8)
        return progress

    def handle_failure(
        self,
        task_id: str,
        error_type: str,
        error_message: Optional[str] = None
    ):
        """
        处理任务失败

        Args:
            task_id: 任务ID
            error_type: 错误类型
            error_message: 错误信息
        """
        ctx = self.get_task_context(task_id)
        ctx["last_error_type"] = error_type
        ctx["last_error_message"] = error_message

        # 更新任务状态为失败
        self.task_manager.update_task(task_id, status=TaskStatus.FAILED)

    def schedule_retry(self, task_id: str):
        """
        调度重试

        Args:
            task_id: 任务ID
        """
        ctx = self.get_task_context(task_id)
        error_type = ctx["last_error_type"]

        if is_retriable(error_type):
            # 可重试错误
            retry_count = ctx["retry_count"] + 1
            ctx["retry_count"] = retry_count

            if retry_count <= 3:
                self.task_manager.update_task(task_id, status=TaskStatus.RETRYING)
            else:
                # 3次重试后进入人工介入
                self.task_manager.update_task(
                    task_id,
                    status=TaskStatus.HUMAN_INTERVENTION
                )
                self.release_employee(
                    self.task_manager.get_task(task_id).assigned_employee
                )
        else:
            # 不可重试错误直接进入人工介入
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.HUMAN_INTERVENTION
            )
            self.release_employee(
                self.task_manager.get_task(task_id).assigned_employee
            )

    def complete_task(self, task_id: str):
        """
        完成任务

        Args:
            task_id: 任务ID
        """
        task = self.task_manager.get_task(task_id)

        # 更新任务状态为完成
        self.task_manager.update_task(task_id, status=TaskStatus.COMPLETED)

        # 释放员工
        if task.assigned_employee:
            self.release_employee(task.assigned_employee)

    # ==================== V2新增：Session生命周期管理 ====================

    def create_session(self, task_id: str) -> str:
        """
        为任务创建Session

        Args:
            task_id: 任务ID

        Returns:
            生成的session_id
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        # 创建Session信息
        self._sessions[session_id] = {
            "task_id": task_id,
            "state": "running",
            "created_at": datetime.now().isoformat(),
        }

        # 关联任务到Session
        self._task_sessions[task_id] = session_id

        # 更新任务的session_id字段
        task = self.task_manager.get_task(task_id)
        task.session_id = session_id
        self.task_manager._save_tasks()

        return session_id

    def get_session_state(self, session_id: str) -> str:
        """
        获取Session状态

        Args:
            session_id: Session ID

        Returns:
            Session状态：running | completed | failed
        """
        session = self._sessions.get(session_id)
        if session:
            return session["state"]
        return "unknown"

    def end_session(self, session_id: str):
        """
        结束Session

        Args:
            session_id: Session ID
        """
        if session_id in self._sessions:
            self._sessions[session_id]["state"] = "completed"
            self._sessions[session_id]["ended_at"] = datetime.now().isoformat()

    def get_session_by_task(self, task_id: str) -> Optional[str]:
        """
        通过任务获取Session

        Args:
            task_id: 任务ID

        Returns:
            关联的session_id，不存在返回None
        """
        return self._task_sessions.get(task_id)

    # ==================== V2.1.0新增：子任务检测与质量检查 ====================

    def detect_and_handle_completion(
        self,
        task_id: str,
        output: str,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        检测子任务完成并处理

        Args:
            task_id: 任务ID
            output: Claude Code输出文本
            tool_results: 工具调用结果列表

        Returns:
            Tuple[bool, Optional[str]]:
                - 是否检测到完成
                - 需注入的prompt（如SUMMARY_PROMPT_TEMPLATE）或None
        """
        result = self._subtask_detector.detect_completion(
            task_id, output, tool_results
        )

        if result.is_complete:
            # 记录完成类型到上下文
            ctx = self.get_task_context(task_id)
            ctx["last_completion_type"] = result.completion_type.value
            ctx["last_completion_details"] = result.details

            # 返回需要注入的总结prompt
            return True, SUMMARY_PROMPT_TEMPLATE

        return False, None

    def parse_quality_check(self, output: str) -> Tuple[Optional[int], bool]:
        """
        从总结输出中解析质量检查结果

        Args:
            output: 包含总结和质量自评的输出文本

        Returns:
            Tuple[Optional[int], bool]:
                - 质量评分（1-10），解析失败返回None
                - 是否有疑虑需人工确认
        """
        # 提取质量评分
        quality_score = None
        quality_match = re.search(r"自评质量[（(].*?[）)]\s*[:：]?\s*(\d+)", output)
        if quality_match:
            try:
                quality_score = int(quality_match.group(1))
                if quality_score < 1 or quality_score > 10:
                    quality_score = None
            except ValueError:
                pass

        # 提取疑虑标记
        doubt_flag = False
        doubt_match = re.search(
            r"是否有疑虑需人工确认[？?].*?[（(].*?[）)]\s*[:：]?\s*(是|yes|y)",
            output,
            re.IGNORECASE
        )
        if doubt_match:
            doubt_flag = True

        return quality_score, doubt_flag

    def should_pause_for_review(self, task_id: str) -> bool:
        """
        判断任务是否需要暂停等待人工确认

        Args:
            task_id: 任务ID

        Returns:
            是否需要暂停
        """
        task = self.task_manager.get_task(task_id)

        # 检查pause_on_doubt配置和质量标记
        if task.pause_on_doubt and task.doubt_flag:
            return True

        # 检查质量评分过低（<6分）
        if task.quality_score is not None and task.quality_score < 6:
            return True

        return False

    def update_quality_metrics(
        self,
        task_id: str,
        quality_score: Optional[int],
        doubt_flag: bool
    ):
        """
        更新任务质量指标

        Args:
            task_id: 任务ID
            quality_score: 质量评分
            doubt_flag: 是否有疑虑
        """
        task = self.task_manager.get_task(task_id)
        task.quality_score = quality_score
        task.doubt_flag = doubt_flag
        self.task_manager._save_tasks()

    def clear_subtask_state(self, task_id: str):
        """
        清除子任务状态（进入下一子任务前调用）

        Args:
            task_id: 任务ID
        """
        self._subtask_detector.clear_pending_edits(task_id)
        ctx = self.get_task_context(task_id)
        ctx.pop("last_completion_type", None)
        ctx.pop("last_completion_details", None)