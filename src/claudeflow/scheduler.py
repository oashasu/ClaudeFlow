"""流程调度模块 - 任务流程调度

V1核心功能：员工分配、阶段推进、失败处理、重试调度
V2新增功能：Session生命周期管理
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from claudeflow.state_machine import (
    TaskStatus, Phase, StateMachine,
    is_retriable, get_retry_interval
)
from claudeflow.task_manager import TaskManager


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