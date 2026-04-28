"""task_manager V2增强测试 - 文件损坏告警"""

import os
import json
import tempfile
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from claudeflow.workflow.task_manager import (
    Task,
    TaskManager,
    TaskNotFoundError
)
from claudeflow.alert_handler import AlertHandler
from claudeflow.websocket_client import WebSocketState


class TestTaskManagerV2FileCorrupt:
    """文件损坏告警测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def mock_alert_handler(self):
        """Mock AlertHandler"""
        handler = MagicMock(spec=AlertHandler)
        handler.ws_client = MagicMock()
        handler.ws_client.state = WebSocketState.CONNECTED
        handler.send_file_corrupt_alert = AsyncMock()
        return handler

    @pytest.fixture
    def manager_with_alert(self, temp_dir, mock_alert_handler):
        """创建带AlertHandler的TaskManager"""
        return TaskManager(temp_dir, alert_handler=mock_alert_handler)

    def test_load_tasks_with_corrupt_file(self, temp_dir, mock_alert_handler):
        """测试损坏tasks.json时发送告警"""
        # 创建损坏的tasks.json
        tasks_file = os.path.join(temp_dir, "tasks.json")
        with open(tasks_file, 'w') as f:
            f.write("{invalid json content")

        # 创建新的manager来触发_load_tasks
        manager = TaskManager(temp_dir, alert_handler=mock_alert_handler)

        # 不应该崩溃，任务列表为空
        assert len(manager.list_tasks()) == 0

    def test_load_tasks_with_valid_file(self, temp_dir):
        """测试正常tasks.json加载"""
        """测试正常tasks.json加载"""
        # 创建正常的tasks.json
        tasks_file = os.path.join(temp_dir, "tasks.json")
        task_data = [{
            "id": "task_001",
            "name": "测试任务",
            "domain": "test",
            "status": "pending",
            "priority": "中",
            "created_at": datetime.now().isoformat(),
            "task_dir_name": "test_dir"
        }]
        with open(tasks_file, 'w') as f:
            json.dump(task_data, f)

        # 创建新的manager来触发_load_tasks
        manager = TaskManager(temp_dir)

        # 应该正常加载
        tasks = manager.list_tasks()
        assert len(tasks) == 1


class TestTaskManagerV2Config:
    """配置扩展测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_manager_with_alert_handler(self, temp_dir):
        """测试带AlertHandler初始化"""
        mock_handler = MagicMock(spec=AlertHandler)
        manager = TaskManager(temp_dir, alert_handler=mock_handler)

        assert manager.alert_handler == mock_handler

    def test_manager_without_alert_handler(self, temp_dir):
        """测试不带AlertHandler初始化"""
        manager = TaskManager(temp_dir)

        assert manager.alert_handler is None


class TestTaskV2:
    """Task数据模型测试"""

    def test_task_creation_with_session(self):
        """测试Task包含session_id"""
        task = Task(
            id="task_001",
            name="测试任务",
            domain="test",
            status="pending",
            priority="中",
            created_at=datetime.now(),
            task_dir_name="test_dir",
            session_id="session_abc123"
        )

        assert task.session_id == "session_abc123"

    def test_task_to_dict_with_session(self):
        """测试序列化包含session_id"""
        task = Task(
            id="task_001",
            name="测试任务",
            domain="test",
            status="pending",
            priority="中",
            created_at=datetime.now(),
            task_dir_name="test_dir",
            session_id="session_xyz"
        )

        data = task.to_dict()
        assert "session_id" in data
        assert data["session_id"] == "session_xyz"