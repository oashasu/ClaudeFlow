"""状态机模块单元测试

七状态模型：待执行、执行中、已完成、已失败、重试中、人工介入点、已归档
"""

import pytest
from enum import Enum


class TestTaskStatus:
    """任务状态枚举测试"""

    def test_status_enum_has_seven_states(self):
        """测试：七状态枚举完整"""
        # 验证：包含全部七种状态
        expected_states = [
            "PENDING", "RUNNING", "COMPLETED", "FAILED",
            "RETRYING", "HUMAN_INTERVENTION", "ARCHIVED"
        ]
        # 先导入模块验证枚举定义
        from claudeflow.state_machine import TaskStatus

        for state in expected_states:
            assert hasattr(TaskStatus, state), f"缺少状态: {state}"

    def test_status_enum_values_are_unique(self):
        """测试：状态值唯一"""
        from claudeflow.state_machine import TaskStatus

        values = [s.value for s in TaskStatus]
        assert len(values) == len(set(values)), "状态值有重复"


class TestStateMachine:
    """状态流转测试"""

    def test_pending_to_running_valid(self):
        """测试：待执行→执行中 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        new_status = sm.transition(TaskStatus.PENDING, "assign_employee")
        assert new_status == TaskStatus.RUNNING

    def test_running_to_completed_valid(self):
        """测试：执行中→已完成 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        new_status = sm.transition(TaskStatus.RUNNING, "success")
        assert new_status == TaskStatus.COMPLETED

    def test_running_to_failed_valid(self):
        """测试：执行中→已失败 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        new_status = sm.transition(TaskStatus.RUNNING, "fail")
        assert new_status == TaskStatus.FAILED

    def test_running_to_paused_valid(self):
        """测试：执行中→已暂停 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        new_status = sm.transition(TaskStatus.RUNNING, "pause")
        assert new_status == TaskStatus.PENDING  # 暂停回到待执行状态

    def test_failed_to_retrying_valid(self):
        """测试：已失败→重试中 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        sm.context["retry_count"] = 0
        new_status = sm.transition(TaskStatus.FAILED, "retry")
        assert new_status == TaskStatus.RETRYING

    def test_retrying_to_running_valid(self):
        """测试：重试中→执行中 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        sm.context["retry_count"] = 1
        new_status = sm.transition(TaskStatus.RETRYING, "retry_success")
        assert new_status == TaskStatus.RUNNING

    def test_retrying_to_human_intervention_after_3_failures(self):
        """测试：重试3次后→人工介入点"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        sm.context["retry_count"] = 3
        new_status = sm.transition(TaskStatus.RETRYING, "retry_fail")
        assert new_status == TaskStatus.HUMAN_INTERVENTION

    def test_invalid_transition_raises_error(self):
        """测试：非法状态跳转被拒绝"""
        from claudeflow.state_machine import StateMachine, TaskStatus, InvalidTransitionError

        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition(TaskStatus.PENDING, "success")  # 不能直接跳到完成

    def test_completed_to_archived_valid(self):
        """测试：已完成→已归档 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        new_status = sm.transition(TaskStatus.COMPLETED, "archive")
        assert new_status == TaskStatus.ARCHIVED

    def test_human_intervention_to_resolved_valid(self):
        """测试：人工介入点→已解决 正确流转"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        new_status = sm.transition(TaskStatus.HUMAN_INTERVENTION, "resolve")
        assert new_status == TaskStatus.COMPLETED


class TestRetryStrategy:
    """重试策略测试"""

    def test_retry_count_increment(self):
        """测试：重试次数正确递增"""
        from claudeflow.state_machine import StateMachine, TaskStatus

        sm = StateMachine()
        sm.context["retry_count"] = 0
        sm.transition(TaskStatus.FAILED, "retry")
        assert sm.context["retry_count"] == 1

    def test_retry_interval_sequence(self):
        """测试：重试间隔正确递增 10s→60s→300s"""
        from claudeflow.state_machine import get_retry_interval

        assert get_retry_interval(1) == 10
        assert get_retry_interval(2) == 60
        assert get_retry_interval(3) == 300

    def test_retriable_error_types(self):
        """测试：可重试错误类型"""
        from claudeflow.state_machine import is_retriable

        assert is_retriable("network_timeout") == True
        assert is_retriable("api_rate_limit") == True
        assert is_retriable("process_crash") == True

    def test_non_retriable_error_types(self):
        """测试：不可重试错误类型"""
        from claudeflow.state_machine import is_retriable

        assert is_retriable("permission_denied") == False
        assert is_retriable("logic_error") == False
        assert is_retriable("invalid_params") == False


class TestPhaseNode:
    """阶段节点测试"""

    def test_phase_enum_has_eight_phases(self):
        """测试：八阶段枚举完整"""
        from claudeflow.state_machine import Phase

        expected_phases = [
            "REQUIREMENTS", "BRAINSTORM", "ARCHITECTURE",
            "DESIGN", "DEVELOPMENT", "TESTING", "REVIEW", "ACCEPTANCE"
        ]
        for phase in expected_phases:
            assert hasattr(Phase, phase), f"缺少阶段: {phase}"

    def test_phase_sequence_order(self):
        """测试：阶段顺序正确"""
        from claudeflow.state_machine import Phase

        phases = list(Phase)
        expected_order = [
            Phase.REQUIREMENTS, Phase.BRAINSTORM, Phase.ARCHITECTURE,
            Phase.DESIGN, Phase.DEVELOPMENT, Phase.TESTING,
            Phase.REVIEW, Phase.ACCEPTANCE
        ]
        assert phases == expected_order

    def test_phase_checkpoint_filename(self):
        """测试：阶段checkpoint文件命名正确"""
        from claudeflow.state_machine import Phase

        assert Phase.REQUIREMENTS.checkpoint_file == "v1_init.json"
        assert Phase.BRAINSTORM.checkpoint_file == "v2_brainstorm.json"
        assert Phase.DEVELOPMENT.checkpoint_file == "v5_dev.json"