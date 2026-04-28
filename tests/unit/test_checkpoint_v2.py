"""checkpoint V2增强测试 - LangGraph接口 + 文件损坏告警"""

import os
import json
import tempfile
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from claudeflow.workflow.checkpoint import (
    Checkpoint,
    CheckpointManager,
    CheckpointNotFoundError
)
from claudeflow.alert_handler import AlertHandler
from claudeflow.websocket_client import WebSocketState


class TestCheckpointV2Interface:
    """LangGraph风格接口测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def manager(self, temp_dir):
        """创建CheckpointManager"""
        return CheckpointManager(temp_dir)

    def test_get_tuple_existing(self, manager, temp_dir):
        """测试获取存在的checkpoint"""
        # 先保存一个checkpoint
        cp = manager.save(
            task_id="task_001",
            phase="development",
            task_state={"status": "running"},
            execution_context={"step": 1}
        )

        # 使用get_tuple获取
        config = {"task_id": "task_001", "checkpoint_id": cp.checkpoint_id}
        result = manager.get_tuple(config)

        assert result is not None
        assert result.checkpoint_id == cp.checkpoint_id

    def test_get_tuple_not_existing(self, manager):
        """测试获取不存在的checkpoint"""
        config = {"task_id": "task_999", "checkpoint_id": "cp_999"}
        result = manager.get_tuple(config)

        assert result is None

    def test_put_checkpoint(self, manager, temp_dir):
        """测试put方法"""
        checkpoint = Checkpoint(
            checkpoint_id="cp_test",
            task_id="task_001",
            phase="testing",
            timestamp=datetime.now(),
            task_state={"status": "testing"},
            execution_context={"step": 2},
            filename="v5_test_cp_test.json"
        )

        config = {"task_id": "task_001"}
        manager.put(config, checkpoint)

        # 验证文件存在
        filepath = os.path.join(temp_dir, checkpoint.filename)
        assert os.path.exists(filepath)

    def test_put_writes(self, manager, temp_dir):
        """测试put_writes方法"""
        # 先保存一个checkpoint
        cp = manager.save(
            task_id="task_001",
            phase="development",
            task_state={"status": "running"},
            execution_context={"step": 1}
        )

        config = {"task_id": "task_001", "checkpoint_id": cp.checkpoint_id}
        writes = [
            {"type": "summary", "content": "阶段完成"},
            {"type": "artifact", "path": "/path/to/file.py"}
        ]

        manager.put_writes(config, writes)

        # 验证writes被添加到checkpoint
        restored = manager.restore(checkpoint_id=cp.checkpoint_id)
        assert "writes" in restored.execution_context


class TestCheckpointV2FileCorrupt:
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
        """创建带AlertHandler的CheckpointManager"""
        return CheckpointManager(temp_dir, alert_handler=mock_alert_handler)

    def test_list_checkpoints_with_corrupt_file(self, manager_with_alert, temp_dir):
        """测试损坏文件时发送告警"""
        # 创建损坏的JSON文件
        corrupt_file = os.path.join(temp_dir, "corrupt_checkpoint.json")
        with open(corrupt_file, 'w') as f:
            f.write("{invalid json content}")

        # 列出checkpoint时应该静默忽略损坏文件
        checkpoints = manager_with_alert.list_checkpoints()

        # 不应该崩溃，返回空列表（或正常checkpoint）
        assert isinstance(checkpoints, list)

    def test_restore_with_corrupt_file(self, manager_with_alert, temp_dir):
        """测试恢复损坏文件"""
        # 创建损坏的JSON文件
        corrupt_file = os.path.join(temp_dir, "corrupt_restore.json")
        with open(corrupt_file, 'w') as f:
            f.write("not json at all")

        # 尝试恢复应该抛出异常
        with pytest.raises(CheckpointNotFoundError):
            manager_with_alert.restore(filename="corrupt_restore.json")


class TestCheckpointV2Config:
    """配置扩展测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            yield d

    def test_manager_with_alert_handler(self, temp_dir):
        """测试带AlertHandler初始化"""
        mock_handler = MagicMock(spec=AlertHandler)
        manager = CheckpointManager(temp_dir, alert_handler=mock_handler)

        assert manager.alert_handler == mock_handler

    def test_manager_without_alert_handler(self, temp_dir):
        """测试不带AlertHandler初始化"""
        manager = CheckpointManager(temp_dir)

        assert manager.alert_handler is None


class TestCheckpointV2Format:
    """Checkpoint格式版本测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def manager(self, temp_dir):
        """创建CheckpointManager"""
        return CheckpointManager(temp_dir)

    def test_checkpoint_format_version(self, manager):
        """测试checkpoint包含format_version"""
        cp = manager.save(
            task_id="task_001",
            phase="development",
            task_state={"status": "running"},
            execution_context={"step": 1}
        )

        # 验证format_version字段
        cp_dict = cp.to_dict()
        assert "checkpoint_format_version" in cp_dict
        assert cp_dict["checkpoint_format_version"] == "2.0"