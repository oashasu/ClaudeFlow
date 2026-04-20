"""HaikuClient单元测试"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

from claudeflow.haiku_client import HaikuClient, HaikuConfig


class TestHaikuClient:
    """Haiku客户端测试"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        client = HaikuClient()
        assert client.config.model == "claude-haiku-4-5-20251001"
        assert client.config.max_tokens == 500
        assert client.config.temperature == 0.3

    def test_init_custom_config(self):
        """测试自定义配置"""
        config = HaikuConfig(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            temperature=0.5
        )
        client = HaikuClient(config)
        assert client.config.model == "claude-sonnet-4-6"
        assert client.config.max_tokens == 1000
        assert client.config.temperature == 0.5

    def test_mock_mode_without_anthropic(self):
        """测试无anthropic库时的Mock模式"""
        # 当anthropic为None时，client._mock_mode应为True
        with patch('claudeflow.haiku_client.anthropic', None):
            client = HaikuClient()
            assert client._mock_mode == True

    @pytest.mark.asyncio
    async def test_mock_response(self):
        """测试Mock响应"""
        client = HaikuClient()
        # 强制Mock模式
        client._mock_mode = True
        client._client = None

        result = await client.call("test prompt")

        assert result["quality_score"] == 7
        assert "Mock" in result["strengths"][0]

    @pytest.mark.asyncio
    async def test_call_returns_json(self):
        """测试调用返回JSON结构"""
        client = HaikuClient()
        client._mock_mode = True
        client._client = None

        result = await client.call("请评估质量")

        # 验证返回结构
        assert "quality_score" in result
        assert "strengths" in result
        assert "improvements" in result
        assert "lessons_learned" in result

    def test_extract_json_valid(self):
        """测试从文本提取有效JSON"""
        client = HaikuClient()

        text = """
        这里是一些文本
        {"quality_score": 8, "strengths": ["测试"]}
        继续文本
        """

        result = client._extract_json(text)

        assert result["quality_score"] == 8
        assert result["strengths"] == ["测试"]

    def test_extract_json_invalid(self):
        """测试无效JSON返回默认值"""
        client = HaikuClient()

        text = "没有JSON内容的文本"

        result = client._extract_json(text)

        assert result["quality_score"] == 0
        assert "API调用失败" in result["improvements"][0]

    def test_default_response(self):
        """测试默认响应结构"""
        client = HaikuClient()

        result = client._default_response()

        assert result["quality_score"] == 0
        assert len(result["strengths"]) == 0
        assert len(result["lessons_learned"]) == 0


class TestHaikuConfig:
    """Haiku配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = HaikuConfig()
        assert config.model.startswith("claude-haiku")
        assert config.api_key is None

    def test_custom_api_key(self):
        """测试自定义API Key"""
        config = HaikuConfig(api_key="sk-test-key")
        assert config.api_key == "sk-test-key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])