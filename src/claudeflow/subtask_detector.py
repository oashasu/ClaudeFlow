"""子任务完成检测模块 - V2.1.0新增

检测Claude Code CLI执行子任务完成的标志，用于在自然边界点阻断并触发checkpoint。

检测优先级：
1. 显式标记：# SUBTASK_COMPLETE
2. 测试通过：pytest输出包含passed
3. 文件创建完成：Write工具使用且无pending edits
"""

from dataclasses import dataclass
from typing import Tuple, Optional, List, Dict, Any
from enum import Enum


class CompletionType(Enum):
    """完成类型"""
    EXPLICIT_MARKER = "explicit_marker"  # 显式标记
    TESTS_PASSED = "tests_passed"  # 测试通过
    FILE_CREATED = "file_created"  # 文件创建完成
    NOT_COMPLETE = "not_complete"  # 未完成


@dataclass
class SubtaskCompletionResult:
    """子任务完成检测结果"""
    is_complete: bool
    completion_type: CompletionType
    details: Optional[str] = None


class SubtaskDetector:
    """子任务完成检测器"""

    # 显式完成标记
    COMPLETE_MARKERS = [
        "# SUBTASK_COMPLETE",
        "# COMPLETE",
        "# DONE",
    ]

    def __init__(self):
        """初始化检测器"""
        self._pending_edits: Dict[str, List[str]] = {}  # task_id -> pending files

    def detect_completion(
        self,
        task_id: str,
        output: str,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> SubtaskCompletionResult:
        """
        检测子任务完成

        Args:
            task_id: 任务ID
            output: Claude Code输出文本
            tool_results: 工具调用结果列表（可选）

        Returns:
            SubtaskCompletionResult: 检测结果
        """
        # 优先级1：显式标记
        result = self._check_explicit_marker(output)
        if result.is_complete:
            return result

        # 优先级2：测试通过
        result = self._check_tests_passed(output, tool_results)
        if result.is_complete:
            return result

        # 优先级3：文件创建完成（需确认无pending edits）
        result = self._check_file_created(task_id, output, tool_results)
        if result.is_complete:
            return result

        return SubtaskCompletionResult(
            is_complete=False,
            completion_type=CompletionType.NOT_COMPLETE
        )

    def _check_explicit_marker(self, output: str) -> SubtaskCompletionResult:
        """检查显式完成标记"""
        for marker in self.COMPLETE_MARKERS:
            if marker in output:
                return SubtaskCompletionResult(
                    is_complete=True,
                    completion_type=CompletionType.EXPLICIT_MARKER,
                    details=f"检测到标记: {marker}"
                )
        return SubtaskCompletionResult(
            is_complete=False,
            completion_type=CompletionType.NOT_COMPLETE
        )

    def _check_tests_passed(
        self,
        output: str,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> SubtaskCompletionResult:
        """检查测试通过"""
        # 从输出文本检查
        if "pytest" in output.lower() and "passed" in output.lower():
            # 提取通过数量
            import re
            match = re.search(r"(\d+)\s*passed", output)
            passed_count = match.group(1) if match else "未知"
            return SubtaskCompletionResult(
                is_complete=True,
                completion_type=CompletionType.TESTS_PASSED,
                details=f"测试通过: {passed_count}个"
            )

        # 从工具结果检查
        if tool_results:
            for result in tool_results:
                if result.get("tool_name") == "Bash":
                    cmd = result.get("command", "")
                    output_text = result.get("output", "")
                    if "pytest" in cmd and "passed" in output_text:
                        return SubtaskCompletionResult(
                            is_complete=True,
                            completion_type=CompletionType.TESTS_PASSED,
                            details="pytest测试通过"
                        )

        return SubtaskCompletionResult(
            is_complete=False,
            completion_type=CompletionType.NOT_COMPLETE
        )

    def _check_file_created(
        self,
        task_id: str,
        output: str,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> SubtaskCompletionResult:
        """检查文件创建完成"""
        created_files = []

        if tool_results:
            for result in tool_results:
                if result.get("tool_name") == "Write":
                    file_path = result.get("file_path", "")
                    if file_path:
                        created_files.append(file_path)

        # 检查是否有pending edits
        pending = self._pending_edits.get(task_id, [])
        if created_files and not pending:
            return SubtaskCompletionResult(
                is_complete=True,
                completion_type=CompletionType.FILE_CREATED,
                details=f"文件创建完成: {len(created_files)}个"
            )

        return SubtaskCompletionResult(
            is_complete=False,
            completion_type=CompletionType.NOT_COMPLETE
        )

    def register_pending_edit(self, task_id: str, file_path: str):
        """注册待处理的编辑（用于阻止误判完成）"""
        if task_id not in self._pending_edits:
            self._pending_edits[task_id] = []
        self._pending_edits[task_id].append(file_path)

    def clear_pending_edits(self, task_id: str):
        """清除待处理的编辑"""
        self._pending_edits.pop(task_id, None)

    def get_pending_edits(self, task_id: str) -> List[str]:
        """获取待处理的编辑列表"""
        return self._pending_edits.get(task_id, [])