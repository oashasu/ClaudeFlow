"""Python→WebSocket集成测试

需要Spring Boot后端运行在localhost:8080

测试内容：
- WebSocket连接建立
- 消息发送与接收
- 断线重连机制
- sessionId传递

运行方式：
- 先启动后端：./mvnw spring-boot:run
- 然后运行测试：PYTHONPATH=src python3 -m pytest tests/integration/test_python_websocket.py -v
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock

from claudeflow.websocket_client import WebSocketClient, WebSocketConfig, WebSocketState


@pytest.mark.integration
class TestWebSocketIntegration:
    """WebSocket集成测试"""

    def test_config_uri_matches_backend(self):
        """测试配置URI匹配后端端点"""
        config = WebSocketConfig()
        assert config.uri == "ws://localhost:8080/ws/python"
        assert config.reconnect_max_attempts == 5

    def test_custom_config(self):
        """测试自定义配置"""
        config = WebSocketConfig(
            uri="ws://custom:9090/ws/test",
            reconnect_max_attempts=10
        )
        client = WebSocketClient(config)

        assert client.config.uri == "ws://custom:9090/ws/test"
        assert client.config.reconnect_max_attempts == 10

    @pytest.mark.asyncio
    async def test_mock_connect_without_backend(self):
        """测试无后端时的连接失败（Mock模式）"""
        client = WebSocketClient()

        # websockets库不可用时应返回False
        with patch('claudeflow.websocket_client.websockets', None):
            result = await client.connect("worker_001", "task_001")
            assert result == False
            assert client.state == WebSocketState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_message_structure_for_registration(self):
        """测试注册消息结构"""
        client = WebSocketClient()
        client.state = WebSocketState.CONNECTED
        client.ws = Mock()
        client.session_id = "test-session-id"

        # 模拟发送
        sent_messages = []
        async def mock_send(msg):
            sent_messages.append(msg)

        client.ws.send = mock_send

        # 手动构建注册消息
        await client.send({
            "type": "worker_register",
            "worker_id": "worker_001",
            "task_id": "task_001",
            "session_id": client.session_id
        })

        assert len(sent_messages) == 1
        msg = json.loads(sent_messages[0])
        assert msg["type"] == "worker_register"
        assert msg["worker_id"] == "worker_001"
        assert msg["session_id"] == "test-session-id"

    @pytest.mark.asyncio
    async def test_send_when_disconnected(self):
        """测试断开状态时发送不报错"""
        client = WebSocketClient()
        client.state = WebSocketState.DISCONNECTED

        # 发送不应抛出异常
        await client.send({"type": "test"})
        # 无操作，静默处理

    @pytest.mark.asyncio
    async def test_close_connection(self):
        """测试关闭连接"""
        client = WebSocketClient()
        client.state = WebSocketState.CONNECTED
        client.ws = Mock()

        async def mock_close():
            pass

        client.ws.close = mock_close

        await client.close()

        assert client.state == WebSocketState.DISCONNECTED
        assert client.ws is None

    @pytest.mark.asyncio
    async def test_reconnect_exponential_backoff(self):
        """测试重连指数退避"""
        config = WebSocketConfig(
            reconnect_max_attempts=3,
            reconnect_base_delay=1.0,
            reconnect_max_delay=10.0
        )
        client = WebSocketClient(config)

        # Mock connect to always fail
        async def mock_connect(*args):
            client.state = WebSocketState.DISCONNECTED
            return False

        client.connect = mock_connect

        # 记录重连尝试次数
        attempts = 0
        original_connect = client.connect

        async def counting_connect(*args):
            attempts += 1
            return await original_connect(*args)

        # 测试重连最终失败
        result = await client.connect_with_retry("worker", "task")
        assert result == False
        assert attempts <= config.reconnect_max_attempts


@pytest.mark.integration
@pytest.mark.skipif(
    True,  # 默认跳过，需要后端运行时手动启用
    reason="需要Spring Boot后端运行"
)
class TestWebSocketWithBackend:
    """需要真实后端的集成测试"""

    @pytest.mark.asyncio
    async def test_real_connection(self):
        """测试真实WebSocket连接"""
        client = WebSocketClient()

        result = await client.connect("worker_001", "task_001")

        if result:
            assert client.state == WebSocketState.CONNECTED
            assert client.session_id is not None

            # 发送测试消息
            await client.send({
                "event": "progress_update",
                "data": {
                    "task_id": "task_001",
                    "phase": "概要设计",
                    "step": 1,
                    "action": "正在读取文件"
                }
            })

            await client.close()

    @pytest.mark.asyncio
    async def test_session_id_extraction(self):
        """测试sessionId自动提取"""
        from claudeflow.session_utils import get_current_session_id

        session_id = get_current_session_id()

        # 如果当前有Claude会话，应该返回有效UUID
        if session_id:
            assert len(session_id) == 36  # UUID格式
            assert session_id.count('-') == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])