"""Haiku API客户端 - 低成本异步复盘Agent

V2新增模块：
- Anthropic Haiku API调用
- 异步执行，不阻塞主任务
- JSON输出解析
"""

import json
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

# anthropic库可选，Mock测试时不需要
try:
    import anthropic
except ImportError:
    anthropic = None


@dataclass
class HaikuConfig:
    """Haiku配置"""
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 500
    temperature: float = 0.3
    api_key: Optional[str] = None  # 从环境变量ANTHROPIC_API_KEY读取


class HaikuClient:
    """Haiku API客户端"""

    def __init__(self, config: Optional[HaikuConfig] = None):
        """
        初始化客户端

        Args:
            config: 配置对象
        """
        self.config = config or HaikuConfig()

        if anthropic is None:
            # 无anthropic库时使用Mock模式（用于测试环境）
            self._client = None
            self._mock_mode = True
        else:
            self._client = anthropic.Anthropic(
                api_key=self.config.api_key
            )
            self._mock_mode = False

    async def call(self, prompt: str) -> Dict[str, Any]:
        """
        异步调用Haiku API

        Args:
            prompt: 输入提示词

        Returns:
            Dict: 解析后的JSON响应
        """
        if self._mock_mode:
            # Mock模式返回默认响应
            return self._mock_response(prompt)

        # 实际API调用（同步客户端在异步函数中运行）
        try:
            response = await asyncio.to_thread(
                self._call_sync,
                prompt
            )
            return response
        except Exception:
            # API调用失败返回默认响应
            return self._default_response()

    def _call_sync(self, prompt: str) -> Dict[str, Any]:
        """同步API调用"""
        message = self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # 解析响应
        content = message.content[0].text

        # 尝试解析JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 如果不是纯JSON，尝试提取JSON部分
            return self._extract_json(content)

    def _mock_response(self, prompt: str) -> Dict[str, Any]:
        """Mock响应（测试环境）"""
        return {
            "quality_score": 7,
            "strengths": ["Mock: 测试环境无API调用"],
            "improvements": ["Mock: 测试环境无API调用"],
            "lessons_learned": ["Mock: 测试环境无API调用"]
        }

    def _default_response(self) -> Dict[str, Any]:
        """API失败时的默认响应"""
        return {
            "quality_score": 0,
            "strengths": [],
            "improvements": ["API调用失败，请检查配置"],
            "lessons_learned": []
        }

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """从文本中提取JSON"""
        # 尝试找到JSON块
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # 无法提取，返回默认
        return self._default_response()