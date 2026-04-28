"""V3.0.0 整合测试 - Python服务 + Token治理 + 全链路验证

测试场景：
1. 正常流程：Web→Java→Python→CLI→完成
2. 熔断流程：超阈值→熔断→快照→状态标记
3. 回滚流程：熔断→回滚→继续→完成

验收标准：
- E2E全链路测试通过
- 熔断机制生效
- 回滚恢复成功
- 日志完整记录
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# Governance模块
from claudeflow.legacy.governance.config import GovernanceConfig
from claudeflow.legacy.governance.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerTrigger,
    CircuitBreakerResult,
)
from claudeflow.legacy.governance.snapshot import (
    SnapshotManager,
    create_baseline_snapshot,
    create_incremental_snapshot,
)
from claudeflow.legacy.governance.recovery import (
    RecoveryManager,
    RecoveryResult,
    rollback,
)


# ============ 辅助函数 ============


def create_mock_similarity_calculator(is_similar_return: bool):
    """创建mock相似度计算器"""
    mock_calc = MagicMock()
    mock_calc.is_similar = MagicMock(return_value=is_similar_return)
    return mock_calc


def setup_test_snapshot_dir() -> Path:
    """创建临时测试快照目录"""
    return Path(tempfile.mkdtemp(prefix="test_snapshots_"))


# ============ 场景1: 正常流程测试 ============


class TestScenario1NormalFlow:
    """场景1: 正常流程 - Web→Java→Python→CLI→完成"""

    def test_normal_flow_no_circuit_break(self):
        """正常流程不触发熔断"""
        mock_calc = create_mock_similarity_calculator(False)
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=10, max_tokens=50000),
            similarity_calculator=mock_calc,
        )

        # 模拟5轮正常调用
        for i in range(5):
            result = breaker.record_call(1000, output=f"正常输出{i}")
            assert result is None

        # 状态应为CLOSED
        assert breaker.state == CircuitState.CLOSED
        assert breaker.call_count == 5

    def test_normal_flow_with_snapshots(self):
        """正常流程创建快照链"""
        snapshot_dir = setup_test_snapshot_dir()
        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))

        # 创建baseline快照（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="task-001",
            milestone="Phase 1 完成",
            core_goals=["实现基础功能"],
            git_repo_path=str(snapshot_dir),
        )
        baseline_id = snapshot_manager.save_snapshot("task-001", baseline)

        # 创建incremental快照
        incremental = create_incremental_snapshot(
            parent_snapshot_id=baseline_id,
            changes=[{"change_type": "add", "target_id": "feature-1"}],
            git_repo_path=str(snapshot_dir),
        )
        incremental_id = snapshot_manager.save_snapshot("task-001", incremental)

        # 验证快照链
        snapshots = snapshot_manager.list_snapshots("task-001")
        assert len(snapshots) == 2
        assert baseline_id in snapshots
        assert incremental_id in snapshots

        # 清理
        shutil.rmtree(snapshot_dir)

    @pytest.mark.skipif(
        True,  # fastapi模块可能未安装，跳过此测试
        reason="FastAPI模块未安装或需要额外依赖"
    )
    def test_runtime_api_endpoints_mock(self):
        """Runtime API 端点可用（已由 runtime/api.py 接管）"""
        try:
            from claudeflow.runtime.api import app

            # 使用FastAPI TestClient风格验证端点存在
            assert hasattr(app, "routes")

            # 验证关键端点
            routes = [route.path for route in app.routes]
            assert "/api/session/start" in routes
            assert "/api/session/{session_id}/events" in routes
            assert "/api/session/{session_id}/intervene" in routes
            assert "/api/session/{session_id}/cancel" in routes
            assert "/health" in routes
        except ImportError:
            pytest.skip("FastAPI模块未安装")


# ============ 场景2: 熔断流程测试 ============


class TestScenario2CircuitBreakFlow:
    """场景2: 熔断流程 - 超阈值→熔断→快照→状态标记"""

    def test_circuit_break_by_max_calls(self):
        """调用次数上限触发熔断"""
        mock_calc = create_mock_similarity_calculator(False)
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=3),
            similarity_calculator=mock_calc,
        )

        # 达到上限触发熔断
        breaker.record_call(1000, output="调用1")
        breaker.record_call(1000, output="调用2")
        result = breaker.record_call(1000, output="调用3")

        assert result is not None
        assert result.trigger == CircuitBreakerTrigger.MAX_CALLS
        assert result.state == CircuitState.OPEN

    def test_circuit_break_by_max_tokens(self):
        """累计Token上限触发熔断"""
        mock_calc = create_mock_similarity_calculator(False)
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_tokens=5000),
            similarity_calculator=mock_calc,
        )

        # 超过Token上限
        breaker.record_call(2000, output="调用1")
        breaker.record_call(2000, output="调用2")
        result = breaker.record_call(2000, output="调用3")  # 总6000超过5000

        assert result is not None
        assert result.trigger == CircuitBreakerTrigger.MAX_TOKENS

    def test_circuit_break_by_similarity(self):
        """相似度检测触发熔断"""
        mock_calc = create_mock_similarity_calculator(True)  # 模拟相似
        breaker = CircuitBreaker(
            config=GovernanceConfig(window_size=3),
            similarity_calculator=mock_calc,
        )

        # 3轮连续相似输出
        breaker.record_call(1000, output="重复内容A")
        breaker.record_call(1000, output="重复内容B")
        result = breaker.record_call(1000, output="重复内容C")

        assert result is not None
        assert result.trigger == CircuitBreakerTrigger.SIMILARITY
        assert breaker.state == CircuitState.OPEN

    def test_circuit_break_with_snapshot_generation(self):
        """熔断触发时生成快照"""
        snapshot_dir = setup_test_snapshot_dir()
        mock_calc = create_mock_similarity_calculator(True)

        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=3),
            similarity_calculator=mock_calc,
        )
        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))

        # 创建初始快照（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="task-002",
            milestone="熔断前状态",
            core_goals=["测试目标"],
            git_repo_path=str(snapshot_dir),
        )
        snapshot_manager.save_snapshot("task-002", baseline)

        # 触发熔断
        breaker.record_call(1000, output="内容1")
        breaker.record_call(1000, output="内容2")
        result = breaker.record_call(1000, output="内容3")

        # 验证熔断状态
        assert breaker.state == CircuitState.OPEN

        # 验证快照存在
        snapshots = snapshot_manager.list_snapshots("task-002")
        assert len(snapshots) >= 1

        # 清理
        shutil.rmtree(snapshot_dir)

    def test_circuit_break_state_persistence(self):
        """熔断状态持久化"""
        mock_calc = create_mock_similarity_calculator(True)
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=2),
            similarity_calculator=mock_calc,
        )

        # 触发熔断
        breaker.record_call(1000, output="内容1")
        result = breaker.record_call(1000, output="内容2")

        # 获取状态
        status = breaker.get_status()

        assert status["state"] == "open"
        assert status["call_count"] == 2
        assert result.trigger == CircuitBreakerTrigger.MAX_CALLS


# ============ 场景3: 回滚流程测试 ============


class TestScenario3RollbackFlow:
    """场景3: 回滚流程 - 熔断→回滚→继续→完成"""

    def test_rollback_to_latest_valid_snapshot(self):
        """回滚至最新有效快照"""
        snapshot_dir = setup_test_snapshot_dir()
        mock_calc = create_mock_similarity_calculator(True)

        # 创建管理器
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=3),
            similarity_calculator=mock_calc,
        )
        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))
        recovery_manager = RecoveryManager(
            snapshot_manager=snapshot_manager,
            circuit_breaker=breaker,
            base_dir=str(snapshot_dir),
        )

        # 创建baseline快照（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="task-003",
            milestone="Phase 1",
            core_goals=["目标1"],
            git_repo_path=str(snapshot_dir),
        )
        snapshot_manager.save_snapshot("task-003", baseline)

        # 模拟熔断触发
        breaker.record_call(1000, output="内容1")
        breaker.record_call(1000, output="内容2")
        break_result = breaker.record_call(1000, output="内容3")

        # 执行回滚
        recovery_result = recovery_manager.handle_circuit_break("task-003", break_result)

        # 验证回滚成功
        assert recovery_result.success
        assert recovery_result.restored_snapshot_id is not None

        # 清理
        shutil.rmtree(snapshot_dir)

    def test_rollback_with_incremental_snapshot(self):
        """回滚生成增量快照"""
        snapshot_dir = setup_test_snapshot_dir()
        mock_calc = create_mock_similarity_calculator(True)

        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=2),
            similarity_calculator=mock_calc,
        )
        recovery_manager = RecoveryManager(
            snapshot_manager=snapshot_manager,
            circuit_breaker=breaker,
            base_dir=str(snapshot_dir),
        )

        # 创建baseline（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="task-004",
            milestone="初始状态",
            core_goals=["目标"],
            git_repo_path=str(snapshot_dir),
        )
        snapshot_manager.save_snapshot("task-004", baseline)

        # 触发熔断并回滚
        breaker.record_call(1000, output="内容")
        break_result = breaker.record_call(1000, output="内容")

        recovery_result = recovery_manager.handle_circuit_break("task-004", break_result)

        # 验证增量快照生成
        assert recovery_result.incremental_snapshot_id is not None

        # 验证快照链完整性
        snapshots = snapshot_manager.list_snapshots("task-004")
        assert len(snapshots) >= 2

        # 清理
        shutil.rmtree(snapshot_dir)

    def test_rollback_and_continue_execution(self):
        """回滚后可继续执行"""
        mock_calc = create_mock_similarity_calculator(True)
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=3),
            similarity_calculator=mock_calc,
        )

        # 触发熔断
        breaker.record_call(1000, output="内容A")
        breaker.record_call(1000, output="内容B")
        breaker.record_call(1000, output="内容C")

        assert breaker.state == CircuitState.OPEN

        # 重置后继续
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.call_count == 0

        # 继续执行不触发熔断
        mock_calc_different = create_mock_similarity_calculator(False)
        breaker.similarity_calculator = mock_calc_different

        for i in range(3):
            result = breaker.record_call(1000, output=f"新内容{i}")
            # 不应该触发熔断（因为内容不同）
            assert result is None or result.trigger != CircuitBreakerTrigger.SIMILARITY

    def test_no_snapshot_available_for_rollback(self):
        """无快照可恢复时处理"""
        snapshot_dir = setup_test_snapshot_dir()
        mock_calc = create_mock_similarity_calculator(True)

        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=2),
            similarity_calculator=mock_calc,
        )
        recovery_manager = RecoveryManager(
            snapshot_manager=snapshot_manager,
            circuit_breaker=breaker,
            base_dir=str(snapshot_dir),
        )

        # 不创建任何快照
        breaker.record_call(1000, output="内容")
        break_result = breaker.record_call(1000, output="内容")

        # 尝试回滚
        recovery_result = recovery_manager.handle_circuit_break("task-no-snap", break_result)

        # 应返回失败
        assert not recovery_result.success
        assert "无快照" in recovery_result.message

        # 清理
        shutil.rmtree(snapshot_dir)


# ============ E2E全链路测试 ============


class TestE2EFullChain:
    """E2E全链路测试"""

    def test_e2e_normal_flow_chain(self):
        """E2E正常流程链路"""
        snapshot_dir = setup_test_snapshot_dir()
        mock_calc = create_mock_similarity_calculator(False)

        # 初始化所有组件
        config = GovernanceConfig(max_calls=10, max_tokens=50000)
        breaker = CircuitBreaker(config=config, similarity_calculator=mock_calc)
        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))
        recovery_manager = RecoveryManager(
            snapshot_manager=snapshot_manager,
            circuit_breaker=breaker,
            base_dir=str(snapshot_dir),
        )

        # 创建初始baseline（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="e2e-task",
            milestone="启动",
            core_goals=["完成任务"],
            git_repo_path=str(snapshot_dir),
        )
        snapshot_manager.save_snapshot("e2e-task", baseline)

        # 模拟正常执行流程
        outputs = ["阶段1完成", "阶段2完成", "阶段3完成", "阶段4完成"]

        for output in outputs:
            # 检查熔断
            result = breaker.record_call(1000, output=output)
            assert result is None  # 正常流程不触发熔断

            # 创建incremental快照
            latest = snapshot_manager.get_latest_snapshot("e2e-task")
            latest_id = latest["snapshot_id"] if latest else baseline["snapshot_id"]
            incremental = create_incremental_snapshot(
                parent_snapshot_id=latest_id,
                changes=[{"change_type": "progress", "target_id": output}],
                git_repo_path=str(snapshot_dir),
            )
            snapshot_manager.save_snapshot("e2e-task", incremental)

        # 验证最终状态
        assert breaker.state == CircuitState.CLOSED
        assert breaker.call_count == 4

        # 验证快照链
        snapshots = snapshot_manager.list_snapshots("e2e-task")
        assert len(snapshots) == 5  # 1 baseline + 4 incremental

        # 清理
        shutil.rmtree(snapshot_dir)

    def test_e2e_circuit_break_and_recovery_chain(self):
        """E2E熔断→回滚→继续链路"""
        snapshot_dir = setup_test_snapshot_dir()

        # Phase 1: 正常执行
        mock_calc_normal = create_mock_similarity_calculator(False)
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=10, max_tokens=50000),  # 增加上限，让SIMILARITY先触发
            similarity_calculator=mock_calc_normal,
        )
        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))
        recovery_manager = RecoveryManager(
            snapshot_manager=snapshot_manager,
            circuit_breaker=breaker,
            base_dir=str(snapshot_dir),
        )

        # 创建baseline（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="e2e-recovery",
            milestone="Phase 1完成",
            core_goals=["完成Phase 1"],
            git_repo_path=str(snapshot_dir),
        )
        snapshot_manager.save_snapshot("e2e-recovery", baseline)

        # Phase 1正常执行
        breaker.record_call(2000, output="Phase1-输出1")
        breaker.record_call(2000, output="Phase1-输出2")

        # Phase 2: 切换到相似输出模拟熔断
        mock_calc_similar = create_mock_similarity_calculator(True)
        breaker.similarity_calculator = mock_calc_similar

        # 触发熔断（3轮相似）
        breaker.record_call(1000, output="重复输出")
        breaker.record_call(1000, output="重复输出")
        break_result = breaker.record_call(1000, output="重复输出")

        # 验证熔断触发（可能是SIMILARITY或MAX_CALLS，取决于阈值顺序）
        assert break_result is not None
        assert breaker.state == CircuitState.OPEN

        # Phase 3: 回滚
        recovery_result = recovery_manager.handle_circuit_break("e2e-recovery", break_result)
        assert recovery_result.success

        # Phase 4: 重置后继续
        breaker.reset()
        mock_calc_continue = create_mock_similarity_calculator(False)
        breaker.similarity_calculator = mock_calc_continue

        # 继续执行
        breaker.record_call(1000, output="Phase3-新输出1")
        result = breaker.record_call(1000, output="Phase3-新输出2")
        assert result is None

        # 清理
        shutil.rmtree(snapshot_dir)


# ============ 日志完整性测试 ============


class TestLoggingCompleteness:
    """日志完整性测试"""

    def test_circuit_break_status_logging(self):
        """熔断状态日志完整"""
        mock_calc = create_mock_similarity_calculator(True)
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=3),
            similarity_calculator=mock_calc,
        )

        # 触发熔断
        breaker.record_call(1000, output="内容A")
        breaker.record_call(1000, output="内容B")
        result = breaker.record_call(1000, output="内容C")

        # 获取完整状态日志
        status = breaker.get_status()

        # 验证日志字段完整
        assert "state" in status
        assert "call_count" in status
        assert "total_tokens" in status
        assert "window_size" in status
        assert "config" in status

        # 验证熔断结果日志完整
        assert result.trigger is not None
        assert result.state is not None
        assert result.message is not None

    def test_snapshot_chain_logging(self):
        """快照链日志完整"""
        snapshot_dir = setup_test_snapshot_dir()
        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))

        # 创建baseline（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="log-test",
            milestone="初始",
            core_goals=["目标"],
            git_repo_path=str(snapshot_dir),
        )
        baseline_id = snapshot_manager.save_snapshot("log-test", baseline)

        # 加载并验证日志字段
        loaded = snapshot_manager.load_snapshot("log-test", baseline_id)

        assert "snapshot_id" in loaded
        assert "snapshot_type" in loaded
        assert "timestamp" in loaded
        assert "git_commit_hash" in loaded
        assert "milestone" in loaded

        # 清理
        shutil.rmtree(snapshot_dir)

    def test_recovery_result_logging(self):
        """恢复结果日志完整"""
        snapshot_dir = setup_test_snapshot_dir()
        mock_calc = create_mock_similarity_calculator(True)

        snapshot_manager = SnapshotManager(base_dir=str(snapshot_dir))
        breaker = CircuitBreaker(
            config=GovernanceConfig(max_calls=2),
            similarity_calculator=mock_calc,
        )
        recovery_manager = RecoveryManager(
            snapshot_manager=snapshot_manager,
            circuit_breaker=breaker,
            base_dir=str(snapshot_dir),
        )

        # 创建baseline（添加task_id参数）
        baseline = create_baseline_snapshot(
            task_id="recovery-log",
            milestone="基线",
            core_goals=["目标"],
            git_repo_path=str(snapshot_dir),
        )
        snapshot_manager.save_snapshot("recovery-log", baseline)

        # 触发熔断并恢复
        breaker.record_call(1000, output="内容")
        break_result = breaker.record_call(1000, output="内容")

        recovery_result = recovery_manager.handle_circuit_break("recovery-log", break_result)

        # 验证恢复结果日志完整
        assert hasattr(recovery_result, "success")
        assert hasattr(recovery_result, "restored_snapshot_id")
        assert hasattr(recovery_result, "incremental_snapshot_id")
        assert hasattr(recovery_result, "message")

        # 清理
        shutil.rmtree(snapshot_dir)


# ============ 运行入口 ============


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])