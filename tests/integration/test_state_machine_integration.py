"""集成测试 - 状态机完整流程

测试 StateMachine + TaskManager + Scheduler 协作
"""

import pytest
import tempfile


class TestStateMachineIntegration:
    """状态机集成测试"""

    def test_task_status_enum_values(self):
        """测试：任务状态枚举值"""
        from claudeflow.state_machine import TaskStatus

        # 验证七状态模型
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.RETRYING.value == "retrying"
        assert TaskStatus.HUMAN_INTERVENTION.value == "human_intervention"
        assert TaskStatus.ARCHIVED.value == "archived"

    def test_state_machine_transition_methods(self):
        """测试：状态机转换方法"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()

        # 验证StateMachine有transition方法
        # 测试有效转换（使用action触发）
        new_status = sm.transition(TaskStatus.PENDING, "assign_employee")
        assert new_status == TaskStatus.RUNNING

        new_status = sm.transition(TaskStatus.RUNNING, "success")
        assert new_status == TaskStatus.COMPLETED

    def test_state_machine_with_task_manager(self):
        """测试：状态机与任务管理器协作"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.state_machine import StateMachine, TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            sm = StateMachine()

            # 创建任务
            task = tm.create_task(name="状态转换测试", domain="AT_支付域")
            assert task.status == TaskStatus.PENDING.value

            # 执行转换
            tm.update_task(task.id, status=TaskStatus.RUNNING)
            updated = tm.get_task(task.id)
            assert updated.status == TaskStatus.RUNNING.value


class TestRetryStrategyIntegration:
    """重试策略集成测试"""

    def test_retry_interval_sequence(self):
        """测试：重试间隔序列"""
        from claudeflow.state_machine import get_retry_interval

        intervals = [
            get_retry_interval(1),
            get_retry_interval(2),
            get_retry_interval(3),
            get_retry_interval(4),
        ]

        assert intervals == [10, 60, 300, 300]

    def test_retriable_vs_non_retriable(self):
        """测试：可重试与不可重试错误分类"""
        from claudeflow.state_machine import is_retriable

        # 可重试
        assert is_retriable("network_timeout") == True
        assert is_retriable("api_rate_limit") == True
        assert is_retriable("process_crash") == True

        # 不可重试
        assert is_retriable("permission_denied") == False
        assert is_retriable("logic_error") == False
        assert is_retriable("auth_error") == False


class TestPhaseSequenceIntegration:
    """阶段序列集成测试"""

    def test_phase_sequence_complete(self):
        """测试：完整阶段序列"""
        from claudeflow.state_machine import Phase

        phases = [
            Phase.REQUIREMENTS,
            Phase.BRAINSTORM,
            Phase.ARCHITECTURE,
            Phase.DESIGN,
            Phase.DEVELOPMENT,
            Phase.TESTING,
            Phase.REVIEW,
            Phase.ACCEPTANCE,
        ]

        # 验证顺序
        for i, phase in enumerate(phases):
            assert phase.value == i + 1

    def test_phase_checkpoint_filenames(self):
        """测试：阶段快照文件名"""
        from claudeflow.state_machine import Phase

        expected_filenames = {
            Phase.REQUIREMENTS: "v1_init.json",
            Phase.BRAINSTORM: "v2_brainstorm.json",
            Phase.ARCHITECTURE: "v3_architecture.json",
            Phase.DESIGN: "v4_design.json",
            Phase.DEVELOPMENT: "v5_dev.json",
            Phase.TESTING: "v6_test.json",
            Phase.REVIEW: "v7_review.json",
            Phase.ACCEPTANCE: "v8_acceptance.json",
        }

        for phase, expected in expected_filenames.items():
            assert phase.checkpoint_file == expected