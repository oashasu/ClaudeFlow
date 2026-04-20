"""PhaseReviewer单元测试"""

import pytest
import asyncio
import json
import tempfile
import os
from pathlib import Path

from claudeflow.phase_reviewer import PhaseReviewer
from claudeflow.haiku_client import HaikuClient


class TestPhaseReviewer:
    """阶段复盘测试"""

    def setup_method(self):
        """每个测试方法前初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "tasks"

    def teardown_method(self):
        """每个测试方法后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default(self):
        """测试默认初始化"""
        reviewer = PhaseReviewer()
        assert reviewer.haiku_client is not None

    def test_init_custom_output_dir(self):
        """测试自定义输出目录"""
        reviewer = PhaseReviewer(output_dir=self.output_dir.as_posix())
        assert reviewer.output_dir == self.output_dir.as_posix()

    @pytest.mark.asyncio
    async def test_review_returns_structure(self):
        """测试复盘返回正确结构"""
        reviewer = PhaseReviewer(output_dir=self.output_dir.as_posix())

        # 强制Mock模式
        reviewer.haiku_client._mock_mode = True
        reviewer.haiku_client._client = None

        summary = {
            "key_decisions": ["采用七状态模型"],
            "files_modified": ["state_machine.py"],
            "tests_passed": 47
        }

        result = await reviewer.review("task_001", "概要设计", summary)

        # 验证结构
        assert result["review_type"] == "phase_review"
        assert result["task_id"] == "task_001"
        assert result["phase"] == "概要设计"
        assert "review" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_review_saves_file(self):
        """测试复盘保存到文件"""
        reviewer = PhaseReviewer(output_dir=self.output_dir.as_posix())
        reviewer.haiku_client._mock_mode = True

        summary = {"tests_passed": 10}

        await reviewer.review("task_002", "详细设计", summary)

        # 检查文件是否创建
        expected_file = self.output_dir / "task_002" / "reviews" / "详细设计_review.json"
        assert expected_file.exists()

        # 验证内容
        with open(expected_file, 'r') as f:
            saved = json.load(f)
            assert saved["task_id"] == "task_002"

    @pytest.mark.asyncio
    async def test_review_async_task(self):
        """测试异步任务创建"""
        reviewer = PhaseReviewer(output_dir=self.output_dir.as_posix())
        reviewer.haiku_client._mock_mode = True

        summary = {"tests_passed": 5}

        task = reviewer.review_async("task_003", "测试阶段", summary)

        # 验证返回的是asyncio.Task
        assert isinstance(task, asyncio.Task)

        # 等待完成
        result = await task
        assert result["task_id"] == "task_003"

    def test_build_prompt_contains_summary(self):
        """测试prompt包含总结内容"""
        reviewer = PhaseReviewer()

        summary = {"key_decisions": ["重要决策"]}
        prompt = reviewer._build_prompt("task_001", "概要设计", summary)

        assert "task_001" in prompt
        assert "概要设计" in prompt
        assert "重要决策" in prompt
        assert "quality_score" in prompt

    def test_get_review_existing(self):
        """测试获取存在的复盘"""
        reviewer = PhaseReviewer(output_dir=self.output_dir.as_posix())

        # 先创建复盘
        review_dir = self.output_dir / "task_004" / "reviews"
        review_dir.mkdir(parents=True)
        review_file = review_dir / "概要设计_review.json"

        test_review = {
            "review_type": "phase_review",
            "task_id": "task_004",
            "phase": "概要设计",
            "review": {"quality_score": 8}
        }

        with open(review_file, 'w') as f:
            json.dump(test_review, f)

        # 获取复盘
        result = reviewer.get_review("task_004", "概要设计")
        assert result["task_id"] == "task_004"
        assert result["review"]["quality_score"] == 8

    def test_get_review_not_existing(self):
        """测试获取不存在的复盘"""
        reviewer = PhaseReviewer(output_dir=self.output_dir.as_posix())

        result = reviewer.get_review("task_not_exist", "概要设计")
        assert result is None

    def test_notify_system_structure(self):
        """测试系统通知结构"""
        reviewer = PhaseReviewer()

        notification = reviewer.notify_system("task_001", "概要设计")

        assert notification["type"] == "system"
        assert "task_001" in notification["content"]
        assert "概要设计" in notification["content"]
        assert "复盘已完成" in notification["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])