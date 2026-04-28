"""alert_handler模块测试 - 告警处理"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from claudeflow.alert_handler import (
    AlertHandler,
    AlertMessage,
    FileCorruptAlert,
    InterventionRequestAlert,
    AlertSeverity
)
from claudeflow.websocket_client import WebSocketState


class TestAlertSeverity:
    """告警级别枚举测试"""

    def test_severity_values(self):
        """测试级别值"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertMessage:
    """告警消息数据结构测试"""

    def test_alert_message_creation(self):
        """测试告警消息创建"""
        msg = AlertMessage(
            type="alert",
            severity=AlertSeverity.WARNING,
            task_id="task_001",
            message="检测到异常"
        )
        assert msg.type == "alert"
        assert msg.severity == AlertSeverity.WARNING

    def test_alert_message_to_dict(self):
        """测试序列化"""
        msg = AlertMessage(
            type="alert",
            severity=AlertSeverity.ERROR,
            task_id="task_001",
            message="文件损坏",
            context={"file": "checkpoint.json"}
        )
        data = msg.to_dict()
        assert data["type"] == "alert"
        assert data["severity"] == "error"
        assert "timestamp" in data


class TestFileCorruptAlert:
    """文件损坏告警测试"""

    def test_file_corrupt_alert_creation(self):
        """测试文件损坏告警创建"""
        alert = FileCorruptAlert(
            type="file_corrupt_alert",
            severity=AlertSeverity.WARNING,
            file_path="/path/to/corrupt.json",
            error_type="JSONDecodeError",
            module="checkpoint"
        )
        assert alert.type == "file_corrupt_alert"
        assert alert.error_type == "JSONDecodeError"

    def test_file_corrupt_alert_to_dict(self):
        """测试序列化"""
        alert = FileCorruptAlert(
            type="file_corrupt_alert",
            severity=AlertSeverity.WARNING,
            file_path="/path/to/file.json",
            error_type="JSONDecodeError",
            module="task_manager"
        )
        data = alert.to_dict()
        assert data["error_type"] == "JSONDecodeError"
        assert data["module"] == "task_manager"


class TestInterventionRequestAlert:
    """人工介入请求告警测试"""

    def test_intervention_request_creation(self):
        """测试人工介入请求创建"""
        alert = InterventionRequestAlert(
            type="intervention_request",
            severity=AlertSeverity.CRITICAL,
            task_id="task_001",
            reason="连续失败3次",
            context={"retry_count": 3}
        )
        assert alert.type == "intervention_request"
        assert alert.reason == "连续失败3次"

    def test_intervention_request_to_dict(self):
        """测试序列化"""
        alert = InterventionRequestAlert(
            type="intervention_request",
            severity=AlertSeverity.CRITICAL,
            task_id="task_001",
            reason="需要人工确认",
            context={"step": "review"}
        )
        data = alert.to_dict()
        assert data["reason"] == "需要人工确认"


class TestAlertHandler:
    """告警处理器测试"""

    @pytest.fixture
    def mock_ws_client(self):
        """Mock WebSocket客户端"""
        client = MagicMock()
        client.send = AsyncMock()
        client.state = WebSocketState.CONNECTED
        return client

    @pytest.fixture
    def handler(self, mock_ws_client):
        """创建告警处理器"""
        return AlertHandler(mock_ws_client)

    def test_handler_creation(self, mock_ws_client):
        """测试处理器创建"""
        handler = AlertHandler(mock_ws_client)
        assert handler.ws_client == mock_ws_client

    @pytest.mark.asyncio
    async def test_send_file_corrupt_alert(self, handler, mock_ws_client):
        """测试发送文件损坏告警"""
        await handler.send_file_corrupt_alert(
            file_path="/path/to/corrupt.json",
            error_type="JSONDecodeError",
            module="checkpoint"
        )
        mock_ws_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_intervention_request(self, handler, mock_ws_client):
        """测试发送人工介入请求"""
        await handler.send_intervention_request(
            task_id="task_001",
            reason="连续失败3次",
            context={"retry_count": 3}
        )
        mock_ws_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_dead_loop_alert(self, handler, mock_ws_client):
        """测试发送死循环告警"""
        await handler.send_dead_loop_alert(
            task_id="task_001",
            content="重复思考内容",
            count=10
        )
        mock_ws_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_generic_alert(self, handler, mock_ws_client):
        """测试发送通用告警"""
        await handler.send_alert(
            severity=AlertSeverity.WARNING,
            task_id="task_001",
            message="一般警告"
        )
        mock_ws_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_when_disconnected(self, mock_ws_client):
        """测试断开状态下发送"""
        mock_ws_client.state = WebSocketState.DISCONNECTED
        handler = AlertHandler(mock_ws_client)

        await handler.send_file_corrupt_alert(
            file_path="/path/to/file.json",
            error_type="JSONDecodeError",
            module="checkpoint"
        )
        # 断开状态下不发送
        mock_ws_client.send.assert_not_called()


class TestAlertHandlerBatch:
    """批量告警测试"""

    @pytest.fixture
    def mock_ws_client(self):
        """Mock WebSocket客户端"""
        client = MagicMock()
        client.send = AsyncMock()
        client.state = WebSocketState.CONNECTED
        return client

    @pytest.fixture
    def handler(self, mock_ws_client):
        """创建告警处理器"""
        return AlertHandler(mock_ws_client)

    @pytest.mark.asyncio
    async def test_send_multiple_alerts(self, handler, mock_ws_client):
        """测试发送多个告警"""
        await handler.send_file_corrupt_alert("file1.json", "JSONDecodeError", "checkpoint")
        await handler.send_dead_loop_alert("task_001", "重复内容", 5)
        await handler.send_alert(AlertSeverity.WARNING, "task_001", "警告")

        assert mock_ws_client.send.call_count == 3