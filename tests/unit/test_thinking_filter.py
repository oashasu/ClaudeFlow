"""thinking_filter模块测试 - 过滤thinking + 死循环检测"""

import pytest
from claudeflow.thinking_filter import (
    ThinkingFilter,
    ThinkingFilterConfig,
    DeadLoopAlert
)


class TestThinkingFilterConfig:
    """配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = ThinkingFilterConfig()
        assert config.duplicate_threshold == 5
        assert config.max_thinking_length == 500

    def test_custom_config(self):
        """测试自定义配置"""
        config = ThinkingFilterConfig(
            duplicate_threshold=3,
            max_thinking_length=200
        )
        assert config.duplicate_threshold == 3
        assert config.max_thinking_length == 200


class TestThinkingFilter:
    """Thinking过滤器测试"""

    @pytest.fixture
    def filter_default(self):
        """默认配置过滤器"""
        return ThinkingFilter()

    @pytest.fixture
    def filter_strict(self):
        """严格配置过滤器"""
        return ThinkingFilter(ThinkingFilterConfig(duplicate_threshold=3))

    def test_filter_normal_thinking(self, filter_default):
        """测试正常thinking过滤"""
        thinking_list = [
            "让我分析一下这个问题",
            "好的，我找到了解决方案",
            "继续下一步"
        ]
        filtered = filter_default.filter_thinking(thinking_list)
        assert len(filtered) == 3

    def test_filter_duplicate_thinking(self, filter_default):
        """测试重复thinking过滤"""
        thinking_list = [
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题",# 第6次，超过阈值
            "让我分析一下这个问题"   # 第7次
        ]
        filtered = filter_default.filter_thinking(thinking_list)
        # 阈值是5，所以前5次保留，后面的不保留
        assert len(filtered) == 5

    def test_filter_strict_threshold(self, filter_strict):
        """测试严格阈值过滤"""
        thinking_list = [
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容"# 第4次，超过阈值3
        ]
        filtered = filter_strict.filter_thinking(thinking_list)
        assert len(filtered) == 3

    def test_truncate_long_thinking(self, filter_default):
        """测试截断过长thinking"""
        long_thinking = "这是一个非常长的thinking内容" * 100
        thinking_list = [long_thinking]
        filtered = filter_default.filter_thinking(thinking_list)
        assert len(filtered[0]) <= 500

    def test_mixed_thinking(self, filter_default):
        """测试混合thinking"""
        thinking_list = [
            "正常思考1",
            "正常思考2",
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容",# 超过阈值
            "正常思考3"
        ]
        filtered = filter_default.filter_thinking(thinking_list)
        # 正常思考保留，重复内容超过阈值后不保留
        assert "正常思考1" in filtered
        assert "正常思考2" in filtered
        assert "正常思考3" in filtered
        # 重复内容只保留前5次
        repeat_count = sum(1 for t in filtered if t == "重复内容")
        assert repeat_count == 5

    def test_empty_thinking_list(self, filter_default):
        """测试空列表"""
        filtered = filter_default.filter_thinking([])
        assert len(filtered) == 0


class TestDeadLoopDetection:
    """死循环检测测试"""

    @pytest.fixture
    def filter_default(self):
        """默认配置过滤器"""
        return ThinkingFilter()

    def test_detect_dead_loop_true(self, filter_default):
        """测试检测到死循环"""
        thinking_list = [
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题",
            "让我分析一下这个问题"# 第6次，超过阈值5
        ]
        detected, content = filter_default.detect_dead_loop(thinking_list)
        assert detected is True
        assert content == "让我分析一下这个问题"

    def test_detect_dead_loop_false(self, filter_default):
        """测试未检测到死循环"""
        thinking_list = [
            "思考1",
            "思考2",
            "思考3",
            "思考4",
            "思考5"# 都是不同的内容
        ]
        detected, content = filter_default.detect_dead_loop(thinking_list)
        assert detected is False
        assert content is None

    def test_detect_dead_loop_threshold_boundary(self, filter_default):
        """测试阈值边界"""
        #刚好在阈值边界（5次，未超过）
        thinking_list = [
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容"
        ]
        detected, _ = filter_default.detect_dead_loop(thinking_list)
        assert detected is False# 阈值是5，超过才触发

    def test_detect_dead_loop_with_truncation(self, filter_default):
        """测试截断后的死循环检测"""
        long_thinking = "这是一个很长的重复内容" * 100
        thinking_list = [long_thinking] * 6
        detected, content = filter_default.detect_dead_loop(thinking_list)
        assert detected is True
        assert len(content) <= 500# 内容已被截断

    def test_generate_dead_loop_alert(self, filter_default):
        """测试生成死循环告警"""
        thinking_list = [
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容",
            "重复内容"
        ]
        detected, content = filter_default.detect_dead_loop(thinking_list)
        alert = filter_default.generate_dead_loop_alert(
            task_id="task_001",
            content=content,
            count=6
        )

        assert alert.type == "log_alert"
        assert alert.alert_level == "WARNING"
        assert alert.task_id == "task_001"
        assert alert.duplicate_content == "重复内容"
        assert alert.duplicate_count == 6


class TestDeadLoopAlert:
    """死循环告警数据结构测试"""

    def test_alert_creation(self):
        """测试告警创建"""
        alert = DeadLoopAlert(
            type="log_alert",
            alert_level="WARNING",
            task_id="task_001",
            message="检测到thinking死循环",
            duplicate_content="重复思考内容",
            duplicate_count=10
        )
        assert alert.type == "log_alert"
        assert alert.alert_level == "WARNING"
        assert alert.duplicate_count == 10

    def test_alert_to_dict(self):
        """测试告警序列化"""
        alert = DeadLoopAlert(
            type="log_alert",
            alert_level="WARNING",
            task_id="task_001",
            message="检测到thinking死循环",
            duplicate_content="重复内容",
            duplicate_count=8
        )
        data = alert.to_dict()
        assert data["type"] == "log_alert"
        assert "timestamp" in data