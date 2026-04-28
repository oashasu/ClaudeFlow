"""progress_reporter模块测试 - 进度推送WebSocket"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from claudeflow.legacy.progress_reporter import (
    ProgressReporter,
    ProgressMessage,
    ToolCallMessage
)
from claudeflow.websocket_client import WebSocketState


class TestProgressMessage:
    """进度消息数据结构测试"""

    def test_progress_message_creation(self):
        """测试进度消息创建"""
        msg = ProgressMessage(
            type="progress",
            task_id="task_001",
            phase="development",
            progress=50
        )
        assert msg.type == "progress"
        assert msg.task_id == "task_001"
        assert msg.progress == 50

    def test_progress_message_to_dict(self):
        """测试序列化"""
        msg = ProgressMessage(
            type="progress",
            task_id="task_001",
            phase="testing",
            progress=80,
            message="测试进行中"
        )
        data = msg.to_dict()
        assert data["type"] == "progress"
        assert "timestamp" in data
        assert data["progress"] == 80


class TestToolCallMessage:
    """工具调用消息测试"""

    def test_tool_call_message_creation(self):
        """测试工具调用消息创建"""
        msg = ToolCallMessage(
            type="tool_call_summary",
            task_id="task_001",
            tool_name="Read",
            action="正在读取 state_machine.py"
        )
        assert msg.type == "tool_call_summary"
        assert msg.tool_name == "Read"

    def test_tool_call_message_to_dict(self):
        """测试序列化"""
        msg = ToolCallMessage(
            type="tool_call_summary",
            task_id="task_001",
            tool_name="Edit",
            action="正在修改 checkpoint.py",
            file_path="/path/to/file.py"
        )
        data = msg.to_dict()
        assert data["tool_name"] == "Edit"
        assert "timestamp" in data


class TestProgressReporter:
    """进度报告器测试"""

    @pytest.fixture
    def mock_ws_client(self):
        """Mock WebSocket客户端"""
        client = MagicMock()
        client.send = AsyncMock()
        client.state = WebSocketState.CONNECTED
        return client

    @pytest.fixture
    def reporter(self, mock_ws_client):
        """创建进度报告器"""
        return ProgressReporter(mock_ws_client)

    def test_reporter_creation(self, mock_ws_client):
        """测试报告器创建"""
        reporter = ProgressReporter(mock_ws_client)
        assert reporter.ws_client == mock_ws_client

    @pytest.mark.asyncio
    async def test_send_progress(self, reporter, mock_ws_client):
        """测试发送进度"""
        await reporter.send_progress(
            task_id="task_001",
            phase="development",
            progress=50,
            message="开发进行中"
        )
        mock_ws_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_tool_call(self, reporter, mock_ws_client):
        """测试发送工具调用"""
        await reporter.send_tool_call(
            task_id="task_001",
            tool_name="Read",
            action="正在读取文件",
            file_path="/path/to/file.py"
        )
        mock_ws_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_phase_complete(self, reporter, mock_ws_client):
        """测试发送阶段完成"""
        await reporter.send_phase_complete(
            task_id="task_001",
            phase="testing",
            summary="测试阶段完成，覆盖率80%"
        )
        mock_ws_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_when_disconnected(self, mock_ws_client):
        """测试断开状态下发送"""
        mock_ws_client.state = WebSocketState.DISCONNECTED
        reporter = ProgressReporter(mock_ws_client)

        await reporter.send_progress(
            task_id="task_001",
            phase="development",
            progress=50
        )
        # 断开状态下不发送
        mock_ws_client.send.assert_not_called()


class TestProgressReporterBatch:
    """批量进度报告测试"""

    @pytest.fixture
    def mock_ws_client(self):
        """Mock WebSocket客户端"""
        client = MagicMock()
        client.send = AsyncMock()
        client.state = WebSocketState.CONNECTED
        return client

    @pytest.fixture
    def reporter(self, mock_ws_client):
        """创建进度报告器"""
        return ProgressReporter(mock_ws_client)

    @pytest.mark.asyncio
    async def test_send_multiple_progress(self, reporter, mock_ws_client):
        """测试发送多个进度"""
        await reporter.send_progress(task_id="task_001", phase="phase1", progress=10)
        await reporter.send_progress(task_id="task_001", phase="phase1", progress=30)
        await reporter.send_progress(task_id="task_001", phase="phase1", progress=50)

        assert mock_ws_client.send.call_count == 3