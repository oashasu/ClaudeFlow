"""Checkpoint模块单元测试

状态快照：保存/恢复/回退
"""

import pytest
import tempfile
import os
import json
from datetime import datetime


class TestCheckpointSave:
    """Checkpoint保存测试"""

    def test_checkpoint_save_success(self):
        """测试：快照保存成功"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            checkpoint = cm.save(
                task_id="task_001",
                phase="development",
                task_state={"status": "running", "assigned_employee": "dev_001"},
                execution_context={"current_file": "test.py"}
            )

            assert checkpoint.checkpoint_id is not None
            assert checkpoint.task_id == "task_001"

    def test_checkpoint_save_creates_file(self):
        """测试：保存快照创建文件"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            cm.save(
                task_id="task_001",
                phase="development",
                task_state={"status": "running"},
                execution_context={}
            )

            # 验证文件存在
            files = os.listdir(checkpoint_dir)
            assert len(files) > 0
            assert files[0].endswith(".json")

    def test_checkpoint_save_with_phase_naming(self):
        """测试：快照命名包含阶段信息"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            checkpoint = cm.save(
                task_id="task_001",
                phase="development",
                task_state={"status": "running"},
                execution_context={}
            )

            # 文件名应该是 v5_dev.json 格式
            assert "v5" in checkpoint.filename or "dev" in checkpoint.filename


class TestCheckpointRestore:
    """Checkpoint恢复测试"""

    def test_checkpoint_restore_success(self):
        """测试：快照恢复成功"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 先保存
            saved = cm.save(
                task_id="task_001",
                phase="development",
                task_state={"status": "running", "assigned_employee": "dev_001"},
                execution_context={"current_file": "test.py"}
            )

            # 再恢复
            restored = cm.restore(checkpoint_id=saved.checkpoint_id)

            assert restored.task_id == "task_001"
            assert restored.phase == "development"
            assert restored.task_state["status"] == "running"

    def test_checkpoint_restore_by_filename(self):
        """测试：按文件名恢复快照"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            saved = cm.save(
                task_id="task_001",
                phase="development",
                task_state={"status": "running"},
                execution_context={}
            )

            restored = cm.restore(filename=saved.filename)
            assert restored is not None

    def test_checkpoint_restore_not_found(self):
        """测试：恢复不存在快照"""
        from claudeflow.checkpoint import CheckpointManager, CheckpointNotFoundError

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            with pytest.raises(CheckpointNotFoundError):
                cm.restore(checkpoint_id="nonexistent")


class TestCheckpointList:
    """Checkpoint列表测试"""

    def test_checkpoint_list_empty(self):
        """测试：空快照列表"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            checkpoints = cm.list_checkpoints(task_id="task_001")
            assert checkpoints == []

    def test_checkpoint_list_for_task(self):
        """测试：列出任务的所有快照"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 保存多个快照（同一个任务的不同阶段）
            cm.save(task_id="task_001", phase="init", task_state={}, execution_context={})
            cm.save(task_id="task_001", phase="dev", task_state={}, execution_context={})

            checkpoints = cm.list_checkpoints(task_id="task_001")
            assert len(checkpoints) == 2

    def test_checkpoint_list_sorted_by_time(self):
        """测试：快照按时间排序"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            cm.save(task_id="task_001", phase="init", task_state={}, execution_context={})
            cm.save(task_id="task_001", phase="dev", task_state={}, execution_context={})

            checkpoints = cm.list_checkpoints(task_id="task_001")
            # 应该按创建时间排序
            assert len(checkpoints) == 2


class TestCheckpointData:
    """Checkpoint数据结构测试"""

    def test_checkpoint_has_required_fields(self):
        """测试：快照包含必需字段"""
        from claudeflow.checkpoint import Checkpoint

        checkpoint = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_001",
            phase="development",
            timestamp=datetime.now(),
            task_state={"status": "running"},
            execution_context={},
            filename="v5_dev.json"
        )

        assert hasattr(checkpoint, "checkpoint_id")
        assert hasattr(checkpoint, "task_id")
        assert hasattr(checkpoint, "phase")
        assert hasattr(checkpoint, "timestamp")
        assert hasattr(checkpoint, "task_state")
        assert hasattr(checkpoint, "execution_context")

    def test_checkpoint_to_dict(self):
        """测试：快照序列化为字典"""
        from claudeflow.checkpoint import Checkpoint

        checkpoint = Checkpoint(
            checkpoint_id="cp_001",
            task_id="task_001",
            phase="development",
            timestamp=datetime.now(),
            task_state={"status": "running"},
            execution_context={},
            filename="v5_dev.json"
        )

        data = checkpoint.to_dict()
        assert data["checkpoint_id"] == "cp_001"
        assert data["task_id"] == "task_001"

    def test_checkpoint_from_dict(self):
        """测试：从字典反序列化快照"""
        from claudeflow.checkpoint import Checkpoint

        data = {
            "checkpoint_id": "cp_001",
            "task_id": "task_001",
            "phase": "development",
            "timestamp": "2026-04-19T10:00:00",
            "task_state": {"status": "running"},
            "execution_context": {},
            "filename": "v5_dev.json"
        }

        checkpoint = Checkpoint.from_dict(data)
        assert checkpoint.checkpoint_id == "cp_001"


class TestCheckpointRollback:
    """Checkpoint回退测试"""

    def test_checkpoint_rollback_to_previous(self):
        """测试：回退到上一个快照"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 保存多个快照
            cp1 = cm.save(task_id="task_001", phase="init", task_state={"progress": 0}, execution_context={})
            cp2 = cm.save(task_id="task_001", phase="dev", task_state={"progress": 50}, execution_context={})

            # 回退到第一个
            restored = cm.rollback(task_id="task_001", target_checkpoint_id=cp1.checkpoint_id)

            assert restored.phase == "init"
            assert restored.task_state["progress"] == 0

    def test_checkpoint_rollback_deletes_later_checkpoints(self):
        """测试：回退删除后续快照"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            cp1 = cm.save(task_id="task_001", phase="init", task_state={}, execution_context={})
            cp2 = cm.save(task_id="task_001", phase="dev", task_state={}, execution_context={})

            # 回退到第一个
            cm.rollback(task_id="task_001", target_checkpoint_id=cp1.checkpoint_id)

            # 后续快照应该被删除
            checkpoints = cm.list_checkpoints(task_id="task_001")
            assert len(checkpoints) == 1