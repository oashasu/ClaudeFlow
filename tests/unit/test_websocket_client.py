"""websocket_client模块测试 - WebSocket通信"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from claudeflow.websocket_client import (
    WebSocketClient,
    WebSocketConfig,
    WebSocketState
)


class TestWebSocketConfig:
    """WebSocket配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = WebSocketConfig()
        assert config.uri == "ws://localhost:8080/ws/python"
        assert config.reconnect_max_attempts == 5
        assert config.reconnect_base_delay == 1

    def test_custom_config(self):
        """测试自定义配置"""
        config = WebSocketConfig(
            uri="ws://custom.server:9000/ws",
            reconnect_max_attempts=3,
            reconnect_base_delay=2
        )
        assert config.uri == "ws://custom.server:9000/ws"
        assert config.reconnect_max_attempts == 3


class TestWebSocketClient:
    """WebSocket客户端测试"""

    @pytest.fixture
    def client(self):
        """创建客户端"""
        return WebSocketClient()

    @pytest.fixture
    def client_with_config(self):
        """创建带配置的客户端"""
        config = WebSocketConfig(uri="ws://test.server:8080/ws")
        return WebSocketClient(config)

    def test_client_creation(self, client):
        """测试客户端创建"""
        assert client.state == WebSocketState.DISCONNECTED
        assert client.ws is None

    def test_client_with_custom_config(self, client_with_config):
        """测试自定义配置客户端"""
        assert client_with_config.config.uri == "ws://test.server:8080/ws"

    @pytest.mark.asyncio
    async def test_connect_success(self, client):
        """测试成功连接"""
        # Mock websockets.connect
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        with patch('websockets.connect', new_callable=AsyncMock, return_value=mock_ws):
            result = await client.connect("worker_001", "task_001")
            assert result is True
            assert client.state == WebSocketState.CONNECTED

    @pytest.mark.asyncio
    async def test_connect_failure(self, client):
        """测试连接失败"""
        with patch('websockets.connect', new_callable=AsyncMock, side_effect=Exception("连接失败")):
            result = await client.connect("worker_001", "task_001")
            assert result is False
            assert client.state == WebSocketState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_send_message(self, client):
        """测试发送消息"""
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        client.ws = mock_ws
        client.state = WebSocketState.CONNECTED

        message = {"type": "progress", "task_id": "task_001"}
        await client.send(message)

        mock_ws.send.assert_called_once()
        # 验证发送的是JSON字符串
        call_args = mock_ws.send.call_args[0][0]
        assert json.loads(call_args)["type"] == "progress"

    @pytest.mark.asyncio
    async def test_send_when_disconnected(self, client):
        """测试断开状态下发送"""
        client.state = WebSocketState.DISCONNECTED
        client.ws = None

        message = {"type": "progress", "task_id": "task_001"}
        # 断开状态下发送应该不抛异常
        await client.send(message)

    @pytest.mark.asyncio
    async def test_close(self, client):
        """测试关闭连接"""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        client.ws = mock_ws
        client.state = WebSocketState.CONNECTED

        await client.close()
        mock_ws.close.assert_called_once()
        assert client.state == WebSocketState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_close_when_disconnected(self, client):
        """测试断开状态下关闭"""
        client.state = WebSocketState.DISCONNECTED
        client.ws = None

        await client.close()
        # 不应该抛异常
        assert client.state == WebSocketState.DISCONNECTED

    def test_get_state(self, client):
        """测试获取状态"""
        assert client.get_state() == WebSocketState.DISCONNECTED

        client.state = WebSocketState.CONNECTED
        assert client.get_state() == WebSocketState.CONNECTED


class TestWebSocketReconnect:
    """WebSocket重连测试"""

    @pytest.fixture
    def client(self):
        """创建客户端"""
        config = WebSocketConfig(reconnect_max_attempts=3)
        return WebSocketClient(config)

    @pytest.mark.asyncio
    async def test_reconnect_success_after_failure(self, client):
        """测试失败后重连成功"""
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        # 第一次失败，第二次成功
        call_count = 0
        async def mock_connect(*args, **kwargs):
            call_count += 1
            if call_count == 1:
                raise Exception("第一次失败")
            return mock_ws

        # 需要在函数内部访问call_count
        call_counts = [0]
        async def mock_connect_inner(*args, **kwargs):
            call_counts[0] += 1
            if call_counts[0] == 1:
                raise Exception("第一次失败")
            return mock_ws

        with patch('websockets.connect', new_callable=AsyncMock, side_effect=mock_connect_inner):
            result = await client.connect_with_retry("worker_001", "task_001")
            assert result is True
            assert client.state == WebSocketState.CONNECTED

    @pytest.mark.asyncio
    async def test_reconnect_max_attempts_exceeded(self, client):
        """测试超过最大重连次数"""
        with patch('websockets.connect', new_callable=AsyncMock, side_effect=Exception("总是失败")):
            result = await client.connect_with_retry("worker_001", "task_001")
            assert result is False
            assert client.state == WebSocketState.DISCONNECTED


class TestWebSocketState:
    """WebSocket状态枚举测试"""

    def test_state_values(self):
        """测试状态值"""
        assert WebSocketState.DISCONNECTED.value == "disconnected"
        assert WebSocketState.CONNECTED.value == "connected"
        assert WebSocketState.CONNECTING.value == "connecting"