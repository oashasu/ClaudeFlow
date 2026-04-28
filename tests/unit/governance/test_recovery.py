"""Recovery恢复层单元测试

验收标准：
- 回滚逻辑正确（单元测试验证）
- 异常重试机制正确
- 增量快照生成正确
- 恢复层覆盖率 ≥ 80%
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from claudeflow.legacy.governance.recovery import (
    RecoveryManager,
    RecoveryResult,
    RecoveryError,
    ToolCallError,
    AcceptanceRetryError,
    rollback,
    retry_tool_call,
    handle_acceptance_failure,
)


# ============ Fixtures ============

@pytest.fixture
def temp_dir():
    """临时目录"""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def recovery_manager(temp_dir):
    """恢复管理器实例"""
    from claudeflow.legacy.governance.snapshot import SnapshotManager
    from claudeflow.legacy.governance.circuit_breaker import CircuitBreaker, CircuitState
    from claudeflow.legacy.governance.acceptance import AcceptanceManager

    snapshot_mgr = SnapshotManager(base_dir=temp_dir)

    # Mock CircuitBreaker（避免相似度模型加载）
    mock_circuit = Mock(spec=CircuitBreaker)
    mock_circuit.state = CircuitState.CLOSED
    mock_circuit.trigger_break = Mock()

    # Mock AcceptanceManager
    mock_acceptance = Mock(spec=AcceptanceManager)

    return RecoveryManager(
        snapshot_manager=snapshot_mgr,
        circuit_breaker=mock_circuit,
        acceptance_manager=mock_acceptance,
        base_dir=temp_dir,
    )


@pytest.fixture
def baseline_snapshot():
    """创建测试用baseline快照"""
    return {
        "snapshot_id": "snap_baseline_001",
        "snapshot_type": "baseline",
        "git_commit_hash": "abc1234",
        "timestamp": "2026-04-21T10:00:00Z",
        "milestone": "需求定稿",
        "core_goals": ["目标1", "目标2"],
        "global_constraints": [],
        "architecture_decisions": [],
        "acceptance_criteria": [],
        "dependencies": [],
    }


@pytest.fixture
def incremental_snapshot():
    """创建测试用incremental快照"""
    return {
        "snapshot_id": "snap_inc_001",
        "snapshot_type": "incremental",
        "parent_snapshot_id": "snap_baseline_001",
        "git_commit_hash": "def5678",
        "timestamp": "2026-04-21T12:00:00Z",
        "changes": [
            {
                "change_type": "update",
                "target_id": "D001",
                "old_value": "旧决策",
                "new_value": "新决策",
                "rationale": "性能优化",
            }
        ],
        "acceptance_result": [],
    }


# ============ RecoveryResult 测试 ============

class TestRecoveryResult:
    """RecoveryResult数据类测试"""

    def test_recovery_result_creation(self):
        """测试创建RecoveryResult"""
        result = RecoveryResult(
            success=True,
            restored_snapshot_id="snap_baseline_001",
            message="回滚成功",
        )
        assert result.success is True
        assert result.restored_snapshot_id == "snap_baseline_001"
        assert result.message == "回滚成功"

    def test_recovery_result_with_incremental(self):
        """测试带增量快照ID的RecoveryResult"""
        result = RecoveryResult(
            success=True,
            restored_snapshot_id="snap_baseline_001",
            incremental_snapshot_id="snap_inc_002",
            message="回滚完成，生成增量快照",
        )
        assert result.incremental_snapshot_id == "snap_inc_002"

    def test_recovery_result_failure(self):
        """测试失败的RecoveryResult"""
        result = RecoveryResult(
            success=False,
            message="无法找到有效快照",
        )
        assert result.success is False
        assert result.restored_snapshot_id is None


# ============ RecoveryError 测试 ============

class TestRecoveryErrors:
    """异常类测试"""

    def test_recovery_error(self):
        """测试RecoveryError"""
        error = RecoveryError("回滚失败")
        assert str(error) == "回滚失败"

    def test_tool_call_error(self):
        """测试ToolCallError"""
        error = ToolCallError("FileRead", "行号超出范围")
        assert error.tool_name == "FileRead"
        assert error.reason == "行号超出范围"

    def test_acceptance_retry_error(self):
        """测试AcceptanceRetryError"""
        error = AcceptanceRetryError(3, "覆盖率低于80%")
        assert error.retry_count == 3
        assert error.reason == "覆盖率低于80%"


# ============ rollback 测试 ============

class TestRollback:
    """回滚逻辑测试"""

    def test_rollback_to_baseline(self, recovery_manager, baseline_snapshot):
        """测试回滚到baseline快照"""
        task_id = "test_task_001"

        # 保存baseline快照
        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)

        # 执行回滚
        result = rollback(task_id, recovery_manager)

        assert result.success is True
        assert result.restored_snapshot_id == "snap_baseline_001"
        assert "baseline" in result.message.lower() or "回滚至" in result.message

    def test_rollback_with_invalid_incremental(self, recovery_manager, baseline_snapshot, incremental_snapshot):
        """测试清理无效增量快照"""
        task_id = "test_task_002"

        # 保存baseline和incremental
        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)
        recovery_manager.snapshot_manager.save_snapshot(task_id, incremental_snapshot)

        # 标记incremental为无效（模拟熔断后）
        recovery_manager._invalid_snapshots[task_id] = ["snap_inc_001"]

        # 执行回滚
        result = rollback(task_id, recovery_manager)

        assert result.success is True
        assert result.restored_snapshot_id == "snap_baseline_001"
        # 验证无效快照被清理
        assert "snap_inc_001" not in recovery_manager.snapshot_manager.list_snapshots(task_id)

    def test_rollback_no_snapshot(self, recovery_manager):
        """测试无快照时的回滚"""
        task_id = "test_task_003"

        result = rollback(task_id, recovery_manager)

        assert result.success is False
        assert result.restored_snapshot_id is None
        assert "无快照" in result.message

    def test_rollback_creates_incremental(self, recovery_manager, baseline_snapshot):
        """测试回滚后生成增量快照"""
        task_id = "test_task_004"

        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)
        result = rollback(task_id, recovery_manager)

        assert result.success is True
        assert result.incremental_snapshot_id is not None
        assert result.incremental_snapshot_id.startswith("snap_")

        # 验证增量快照存在
        inc_snap = recovery_manager.snapshot_manager.load_snapshot(
            task_id, result.incremental_snapshot_id
        )
        assert inc_snap is not None
        assert inc_snap["snapshot_type"] == "incremental"
        assert inc_snap["parent_snapshot_id"] == "snap_baseline_001"

    def test_rollback_find_latest_valid(self, recovery_manager, baseline_snapshot):
        """测试找到最新有效快照"""
        task_id = "test_task_005"

        # 保存baseline
        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)

        # 创建多个incremental（确保timestamp递增）
        for i in range(3):
            inc_snap = {
                "snapshot_id": f"snap_inc_{i+1}",
                "snapshot_type": "incremental",
                "parent_snapshot_id": f"snap_inc_{i}" if i > 0 else "snap_baseline_001",
                "git_commit_hash": f"hash{i}",
                "timestamp": f"2026-04-21T{11+i}:00:00Z",  # 11:00, 12:00, 13:00
                "changes": [],
                "acceptance_result": [],
            }
            recovery_manager.snapshot_manager.save_snapshot(task_id, inc_snap)

        # 标记后两个为无效
        recovery_manager._invalid_snapshots[task_id] = ["snap_inc_2", "snap_inc_3"]

        # 执行回滚
        result = rollback(task_id, recovery_manager)

        # 应回滚到snap_inc_1（最后一个有效的）
        assert result.success is True
        assert result.restored_snapshot_id == "snap_inc_1"


# ============ retry_tool_call 测试 ============

class TestRetryToolCall:
    """工具调用重试测试"""

    def test_retry_success_on_first_call(self):
        """测试首次调用成功"""
        mock_func = Mock(return_value="success")

        result = retry_tool_call(mock_func, "arg1", "arg2")

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_success_on_second_call(self):
        """测试第二次调用成功"""
        mock_func = Mock()
        mock_func.side_effect = [ToolCallError("FileRead", "行号错误"), "success"]

        result = retry_tool_call(mock_func, "arg1")

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_fail_after_two_attempts(self):
        """测试两次失败后抛出异常"""
        mock_func = Mock()
        mock_func.side_effect = [
            ToolCallError("FileRead", "行号错误"),
            ToolCallError("FileRead", "行号错误"),
        ]

        with pytest.raises(ToolCallError):
            retry_tool_call(mock_func, "arg1")

        assert mock_func.call_count == 2

    def test_retry_with_kwargs(self):
        """测试带kwargs的重试"""
        mock_func = Mock(return_value="success")

        result = retry_tool_call(mock_func, "arg1", key1="value1")

        assert result == "success"
        mock_func.assert_called_with("arg1", key1="value1")


# ============ handle_acceptance_failure 测试 ============

class TestHandleAcceptanceFailure:
    """验收失败处理测试"""

    def test_first_failure_triggers_correction(self, recovery_manager):
        """测试首次失败触发自动修正"""
        task_id = "test_task_006"

        # Mock acceptance_manager.auto_correct返回True（修正成功）
        recovery_manager.acceptance_manager.auto_correct = Mock(return_value=True)

        result = handle_acceptance_failure(task_id, "覆盖率72%", recovery_manager)

        assert result.success is True
        assert result.message == "自动修正成功"

    def test_three_failures_trigger_circuit_break(self, recovery_manager):
        """测试3次失败触发熔断"""
        task_id = "test_task_007"

        # Mock auto_correct始终返回False
        recovery_manager.acceptance_manager.auto_correct = Mock(return_value=False)
        recovery_manager._acceptance_retry_count[task_id] = 2  # 已失败2次

        # 执行第3次失败处理
        result = handle_acceptance_failure(task_id, "覆盖率72%", recovery_manager)

        assert result.success is False
        assert "熔断" in result.message

        # 验证熔断器被触发
        from claudeflow.legacy.governance.circuit_breaker import CircuitBreakerTrigger
        recovery_manager.circuit_breaker.trigger_break.assert_called()

    def test_retry_count_tracking(self, recovery_manager):
        """测试重试计数追踪"""
        task_id = "test_task_008"

        recovery_manager.acceptance_manager.auto_correct = Mock(return_value=False)

        # 第一次失败
        result1 = handle_acceptance_failure(task_id, "覆盖率72%", recovery_manager)
        assert recovery_manager._acceptance_retry_count[task_id] == 1

        # 第二次失败
        result2 = handle_acceptance_failure(task_id, "覆盖率72%", recovery_manager)
        assert recovery_manager._acceptance_retry_count[task_id] == 2

        # 第三次失败
        result3 = handle_acceptance_failure(task_id, "覆盖率72%", recovery_manager)
        assert recovery_manager._acceptance_retry_count[task_id] == 3

    def test_manual_intervention_entry(self, recovery_manager):
        """测试人工介入入口"""
        task_id = "test_task_009"

        # 模拟达到熔断状态
        recovery_manager.acceptance_manager.auto_correct = Mock(return_value=False)
        recovery_manager._acceptance_retry_count[task_id] = 3

        result = handle_acceptance_failure(task_id, "覆盖率72%", recovery_manager)

        # 应包含人工介入入口
        assert result.manual_intervention_required is True


# ============ RecoveryManager 测试 ============

class TestRecoveryManager:
    """RecoveryManager综合测试"""

    def test_init(self, temp_dir):
        """测试初始化"""
        from claudeflow.legacy.governance.snapshot import SnapshotManager

        snapshot_mgr = SnapshotManager(base_dir=temp_dir)
        manager = RecoveryManager(snapshot_manager=snapshot_mgr, base_dir=temp_dir)

        assert manager.snapshot_manager is snapshot_mgr
        assert manager._invalid_snapshots == {}
        assert manager._acceptance_retry_count == {}

    def test_mark_snapshot_invalid(self, recovery_manager):
        """测试标记无效快照"""
        task_id = "test_task_010"
        snapshot_id = "snap_invalid"

        recovery_manager.mark_snapshot_invalid(task_id, snapshot_id)

        assert snapshot_id in recovery_manager._invalid_snapshots[task_id]

    def test_clear_retry_count(self, recovery_manager):
        """测试清除重试计数"""
        task_id = "test_task_011"
        recovery_manager._acceptance_retry_count[task_id] = 3

        recovery_manager.clear_retry_count(task_id)

        assert task_id not in recovery_manager._acceptance_retry_count

    def test_get_latest_valid_snapshot(self, recovery_manager, baseline_snapshot, incremental_snapshot):
        """测试获取最新有效快照"""
        task_id = "test_task_012"

        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)
        recovery_manager.snapshot_manager.save_snapshot(task_id, incremental_snapshot)

        # 标记incremental无效
        recovery_manager.mark_snapshot_invalid(task_id, "snap_inc_001")

        valid_snap = recovery_manager.get_latest_valid_snapshot(task_id)

        assert valid_snap["snapshot_id"] == "snap_baseline_001"

    def test_cleanup_invalid_snapshots(self, recovery_manager, baseline_snapshot, incremental_snapshot):
        """测试清理无效快照"""
        task_id = "test_task_013"

        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)
        recovery_manager.snapshot_manager.save_snapshot(task_id, incremental_snapshot)

        recovery_manager.mark_snapshot_invalid(task_id, "snap_inc_001")
        recovery_manager.cleanup_invalid_snapshots(task_id)

        # 验证快照被删除
        assert "snap_inc_001" not in recovery_manager.snapshot_manager.list_snapshots(task_id)
        assert "snap_baseline_001" in recovery_manager.snapshot_manager.list_snapshots(task_id)


# ============ 熔断触发恢复测试 ============

class TestCircuitBreakTriggerRecovery:
    """熔断触发恢复场景测试"""

    def test_circuit_break_triggers_rollback(self, recovery_manager, baseline_snapshot):
        """测试熔断触发回滚"""
        task_id = "test_task_014"

        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)

        # 模拟熔断触发
        from claudeflow.legacy.governance.circuit_breaker import CircuitBreakerTrigger, CircuitBreakerResult, CircuitState

        break_result = CircuitBreakerResult(
            trigger=CircuitBreakerTrigger.MAX_CALLS,
            state=CircuitState.OPEN,
            message="调用次数达到上限",
        )

        recovery_result = recovery_manager.handle_circuit_break(task_id, break_result)

        assert recovery_result.success is True
        assert recovery_result.restored_snapshot_id == "snap_baseline_001"
        assert "熔断恢复" in recovery_result.message

    def test_circuit_break_no_snapshot(self, recovery_manager):
        """测试熔断时无快照"""
        task_id = "test_task_015"

        from claudeflow.legacy.governance.circuit_breaker import CircuitBreakerTrigger, CircuitBreakerResult, CircuitState

        break_result = CircuitBreakerResult(
            trigger=CircuitBreakerTrigger.SIMILARITY,
            state=CircuitState.OPEN,
            message="相似度熔断",
        )

        recovery_result = recovery_manager.handle_circuit_break(task_id, break_result)

        assert recovery_result.success is False
        assert "无快照可恢复" in recovery_result.message


# ============ 数据一致性测试 ============

class TestDataConsistency:
    """数据一致性测试"""

    def test_recovery_creates_traceable_snapshot(self, recovery_manager, baseline_snapshot):
        """测试恢复生成可追溯快照"""
        task_id = "test_task_016"

        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)
        result = rollback(task_id, recovery_manager)

        # 获取快照链
        chain = recovery_manager.snapshot_manager.get_snapshot_chain(
            task_id, result.incremental_snapshot_id
        )

        # 验证链完整性
        assert len(chain) == 2
        assert chain[0]["snapshot_type"] == "baseline"
        assert chain[1]["snapshot_type"] == "incremental"
        assert chain[1]["parent_snapshot_id"] == chain[0]["snapshot_id"]

    def test_all_recovery_ops_generate_incremental(self, recovery_manager, baseline_snapshot):
        """测试所有恢复操作生成增量快照"""
        task_id = "test_task_017"

        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)

        # 执行多种恢复操作
        results = []

        # 1. 回滚
        results.append(rollback(task_id, recovery_manager))

        # 2. 熔断恢复
        from claudeflow.legacy.governance.circuit_breaker import CircuitBreakerTrigger, CircuitBreakerResult, CircuitState
        break_result = CircuitBreakerResult(
            trigger=CircuitBreakerTrigger.MAX_TOKENS,
            state=CircuitState.OPEN,
            message="Token上限熔断",
        )
        results.append(recovery_manager.handle_circuit_break(task_id, break_result))

        # 验证每个恢复操作都生成了增量快照
        for result in results:
            if result.success:
                assert result.incremental_snapshot_id is not None


# ============ 边界情况测试 ============

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_changes_in_incremental(self, recovery_manager, baseline_snapshot):
        """测试恢复操作生成正确的增量快照"""
        task_id = "test_task_018"

        recovery_manager.snapshot_manager.save_snapshot(task_id, baseline_snapshot)
        result = rollback(task_id, recovery_manager)

        inc_snap = recovery_manager.snapshot_manager.load_snapshot(
            task_id, result.incremental_snapshot_id
        )

        # 恢复操作必然生成变更记录
        assert len(inc_snap["changes"]) >= 1
        assert inc_snap["changes"][0]["change_type"] == "update"
        assert inc_snap["changes"][0]["target_id"] == "recovery_state"

    def test_concurrent_task_recovery(self, recovery_manager, baseline_snapshot):
        """测试并发任务恢复"""
        task_id_1 = "test_task_019_a"
        task_id_2 = "test_task_019_b"

        # 两个任务各自保存快照
        snap_1 = baseline_snapshot.copy()
        snap_1["snapshot_id"] = "snap_task_001"
        recovery_manager.snapshot_manager.save_snapshot(task_id_1, snap_1)

        snap_2 = baseline_snapshot.copy()
        snap_2["snapshot_id"] = "snap_task_002"
        recovery_manager.snapshot_manager.save_snapshot(task_id_2, snap_2)

        # 分别回滚
        result_1 = rollback(task_id_1, recovery_manager)
        result_2 = rollback(task_id_2, recovery_manager)

        assert result_1.restored_snapshot_id == "snap_task_001"
        assert result_2.restored_snapshot_id == "snap_task_002"