"""Recovery恢复层核心模块

功能：
1. 熔断触发恢复：回滚至上一有效基线快照
2. 工具调用异常恢复：重试1次，失败则人工介入
3. 验收失败恢复：自动修正，3次失败触发熔断
4. 数据一致性：所有恢复操作生成增量快照

设计原则：
- 异常熔断自动回滚至上一有效快照，无状态丢失
- 所有恢复操作生成增量快照，全程可追溯
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Union
from enum import Enum

from claudeflow.legacy.governance.snapshot import (
    SnapshotManager,
    create_incremental_snapshot,
)
from claudeflow.legacy.governance.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerResult,
    CircuitBreakerTrigger,
    CircuitState,
)


# ============ 异常类定义 ============


class RecoveryError(Exception):
    """恢复层基础异常"""
    pass


class ToolCallError(RecoveryError):
    """工具调用失败异常"""

    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"工具 {tool_name} 调用失败: {reason}")


class AcceptanceRetryError(RecoveryError):
    """验收重试失败异常"""

    def __init__(self, retry_count: int, reason: str):
        self.retry_count = retry_count
        self.reason = reason
        super().__init__(f"验收失败 {retry_count} 次: {reason}")


# ============ 结果类定义 ============


@dataclass
class RecoveryResult:
    """恢复操作结果"""

    success: bool
    restored_snapshot_id: Optional[str] = None
    incremental_snapshot_id: Optional[str] = None
    message: str = ""
    manual_intervention_required: bool = False


# ============ 恢复管理器 ============


@dataclass
class RecoveryManager:
    """恢复管理器

    功能：
    1. rollback: 回滚至上一有效快照
    2. handle_circuit_break: 处理熔断触发
    3. handle_acceptance_failure: 处理验收失败
    4. cleanup_invalid_snapshots: 清理无效快照

    内部状态：
    - _invalid_snapshots: 无效快照ID映射
    - _acceptance_retry_count: 验收重试计数
    """

    snapshot_manager: SnapshotManager
    circuit_breaker: Optional[CircuitBreaker] = None
    acceptance_manager: Optional[Any] = None  # AcceptanceManager
    base_dir: str = field(default_factory=lambda: ".")

    # 内部状态：无效快照映射 {task_id: [snapshot_ids]}
    _invalid_snapshots: Dict[str, List[str]] = field(default_factory=dict, init=False)
    # 内部状态：验收重试计数 {task_id: count}
    _acceptance_retry_count: Dict[str, int] = field(default_factory=dict, init=False)

    def rollback(self, task_id: str) -> RecoveryResult:
        """执行回滚

        流程：
        1. 查找最新有效快照
        2. 清理无效增量快照
        3. 生成恢复操作的增量快照

        Args:
            task_id: 任务ID

        Returns:
            RecoveryResult
        """
        # 查找最新有效快照
        valid_snapshot = self.get_latest_valid_snapshot(task_id)

        if valid_snapshot is None:
            return RecoveryResult(
                success=False,
                message=f"任务 {task_id} 无快照可恢复",
            )

        # 清理无效快照
        self.cleanup_invalid_snapshots(task_id)

        # 生成恢复操作的增量快照
        incremental_id = self._create_recovery_incremental(task_id, valid_snapshot)

        return RecoveryResult(
            success=True,
            restored_snapshot_id=valid_snapshot["snapshot_id"],
            incremental_snapshot_id=incremental_id,
            message=f"回滚至 {valid_snapshot['snapshot_type']} 快照 {valid_snapshot['snapshot_id']}",
        )

    def handle_circuit_break(
        self,
        task_id: str,
        break_result: CircuitBreakerResult,
    ) -> RecoveryResult:
        """处理熔断触发

        流程：
        1. 触发回滚
        2. 标记当前状态为熔断恢复

        Args:
            task_id: 任务ID
            break_result: 熔断结果

        Returns:
            RecoveryResult
        """
        # 执行回滚
        result = self.rollback(task_id)

        if not result.success:
            return RecoveryResult(
                success=False,
                message=f"熔断触发但无快照可恢复: {break_result.message}",
            )

        # 更新消息
        result.message = f"熔断恢复 ({break_result.trigger.value}): {result.message}"

        return result

    def handle_acceptance_failure(
        self,
        task_id: str,
        reason: str,
    ) -> RecoveryResult:
        """处理验收失败

        流程：
        1. 增加重试计数
        2. 尝试自动修正
        3. 3次失败触发熔断

        Args:
            task_id: 任务ID
            reason: 失败原因

        Returns:
            RecoveryResult
        """
        # 增加重试计数
        self._acceptance_retry_count[task_id] = self._acceptance_retry_count.get(task_id, 0) + 1
        retry_count = self._acceptance_retry_count[task_id]

        # 尝试自动修正
        corrected = False
        if self.acceptance_manager and hasattr(self.acceptance_manager, "auto_correct"):
            corrected = self.acceptance_manager.auto_correct(task_id, reason)

        if corrected:
            # 修正成功，清除计数
            self.clear_retry_count(task_id)
            return RecoveryResult(
                success=True,
                message="自动修正成功",
            )

        # 检查是否达到熔断阈值（3次）
        if retry_count >= 3:
            # 触发熔断
            if self.circuit_breaker:
                self.circuit_breaker.trigger_break(CircuitBreakerTrigger.MAX_CALLS)

            return RecoveryResult(
                success=False,
                message=f"验收失败 {retry_count} 次，触发熔断: {reason}",
                manual_intervention_required=True,
            )

        return RecoveryResult(
            success=False,
            message=f"验收失败第 {retry_count} 次: {reason}",
        )

    def mark_snapshot_invalid(self, task_id: str, snapshot_id: str) -> None:
        """标记快照为无效

        Args:
            task_id: 任务ID
            snapshot_id: 快照ID
        """
        if task_id not in self._invalid_snapshots:
            self._invalid_snapshots[task_id] = []

        if snapshot_id not in self._invalid_snapshots[task_id]:
            self._invalid_snapshots[task_id].append(snapshot_id)

    def clear_retry_count(self, task_id: str) -> None:
        """清除验收重试计数

        Args:
            task_id: 任务ID
        """
        if task_id in self._acceptance_retry_count:
            del self._acceptance_retry_count[task_id]

    def get_latest_valid_snapshot(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取最新有效快照

        排除无效快照，返回最新的有效快照。

        Args:
            task_id: 任务ID

        Returns:
            最新有效快照字典，或None
        """
        all_snapshots = self.snapshot_manager.list_snapshots(task_id)
        invalid_ids = self._invalid_snapshots.get(task_id, [])

        # 收集所有有效快照
        valid_snapshots = []
        for snap_id in all_snapshots:
            if snap_id in invalid_ids:
                continue

            snap = self.snapshot_manager.load_snapshot(task_id, snap_id)
            if snap:
                valid_snapshots.append(snap)

        if not valid_snapshots:
            return None

        # 按timestamp排序（最新优先）
        valid_snapshots.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
        return valid_snapshots[0]

    def cleanup_invalid_snapshots(self, task_id: str) -> None:
        """清理无效快照

        删除所有标记为无效的快照文件。

        Args:
            task_id: 任务ID
        """
        invalid_ids = self._invalid_snapshots.get(task_id, [])

        for snap_id in invalid_ids:
            self.snapshot_manager.delete_snapshot(task_id, snap_id)

        # 清空无效快照列表
        if task_id in self._invalid_snapshots:
            del self._invalid_snapshots[task_id]

    def _create_recovery_incremental(
        self,
        task_id: str,
        restored_snapshot: Dict[str, Any],
    ) -> str:
        """创建恢复操作的增量快照

        Args:
            task_id: 任务ID
            restored_snapshot: 恢复到的快照

        Returns:
            新增量快照ID
        """
        changes = [
            {
                "change_type": "update",
                "target_id": "recovery_state",
                "old_value": "circuit_break",
                "new_value": "restored",
                "rationale": "熔断恢复操作",
            }
        ]

        incremental_snap = create_incremental_snapshot(
            parent_snapshot_id=restored_snapshot["snapshot_id"],
            changes=changes,
            git_repo_path=self.base_dir,
        )

        return self.snapshot_manager.save_snapshot(task_id, incremental_snap)


# ============ 简化API函数 ============


def rollback(task_id: str, manager: RecoveryManager) -> RecoveryResult:
    """回滚至上一有效快照

    Args:
        task_id: 任务ID
        manager: 恢复管理器

    Returns:
        RecoveryResult
    """
    return manager.rollback(task_id)


def retry_tool_call(
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    """工具调用重试（最多重试1次）

    Args:
        func: 要执行的函数
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        函数返回值

    Raises:
        ToolCallError: 两次调用都失败
    """
    max_retries = 1  # 设计文档：重试1次
    last_error = None

    for attempt in range(max_retries + 1):  # 总共2次尝试
        try:
            return func(*args, **kwargs)
        except ToolCallError as e:
            last_error = e
            if attempt < max_retries:
                # 还有重试机会，继续
                continue

    # 重试耗尽，抛出最后一次错误
    raise last_error


def handle_acceptance_failure(
    task_id: str,
    reason: str,
    manager: RecoveryManager,
) -> RecoveryResult:
    """处理验收失败

    Args:
        task_id: 任务ID
        reason: 失败原因
        manager: 恢复管理器

    Returns:
        RecoveryResult
    """
    return manager.handle_acceptance_failure(task_id, reason)