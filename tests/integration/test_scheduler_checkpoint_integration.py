"""集成测试 - 调度器与Checkpoint协作

测试 Scheduler + CheckpointManager 协作
"""

import pytest
import tempfile
import os


class TestSchedulerCheckpointIntegration:
    """调度器Checkpoint集成测试"""

    def test_checkpoint_save_on_phase_advance(self):
        """测试：阶段推进时保存快照"""
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_dir = os.path.join(tmpdir, "tasks")
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")

            tm = TaskManager(tasks_dir=tasks_dir)
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="快照测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 获取当前阶段并保存快照
            phase = scheduler.get_current_phase(task.id)
            ctx = scheduler.get_task_context(task.id)

            checkpoint = cm.save(
                task_id=task.id,
                phase=phase.value,
                task_state={"status": "running"},
                execution_context=ctx
            )

            assert checkpoint.task_id == task.id
            # phase.value是int类型（Phase枚举值）
            assert checkpoint.phase == 1  # Phase.REQUIREMENTS.value

    def test_checkpoint_restore_after_failure(self):
        """测试：失败后恢复快照"""
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_dir = os.path.join(tmpdir, "tasks")
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")

            tm = TaskManager(tasks_dir=tasks_dir)
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="恢复测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 推进阶段并保存快照
            scheduler.advance_phase(task.id)
            phase = scheduler.get_current_phase(task.id)
            ctx = scheduler.get_task_context(task.id)

            checkpoint = cm.save(
                task_id=task.id,
                phase=phase.value,
                task_state={"progress": 50},
                execution_context=ctx
            )

            # 模拟失败
            scheduler.handle_failure(task.id, "network_error")

            # 恢复快照
            restored = cm.restore(checkpoint_id=checkpoint.checkpoint_id)

            assert restored.task_state["progress"] == 50
            # phase是int类型（Phase枚举值）
            assert restored.phase == 2  # Phase.BRAINSTORM.value

    def test_checkpoint_rollback_flow(self):
        """测试：回退到之前的阶段"""
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_dir = os.path.join(tmpdir, "tasks")
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")

            tm = TaskManager(tasks_dir=tasks_dir)
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="回退测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 保存多个阶段的快照
            cp1 = cm.save(
                task_id=task.id,
                phase="requirements",
                task_state={"phase": 1},
                execution_context={}
            )

            scheduler.advance_phase(task.id)
            scheduler.advance_phase(task.id)

            cp3 = cm.save(
                task_id=task.id,
                phase="architecture",
                task_state={"phase": 3},
                execution_context={}
            )

            # 回退到第一个快照
            restored = cm.rollback(task_id=task.id, target_checkpoint_id=cp1.checkpoint_id)

            assert restored.phase == "requirements"
            assert restored.task_state["phase"] == 1

            # 后续快照应被删除
            checkpoints = cm.list_checkpoints(task_id=task.id)
            assert len(checkpoints) == 1

    def test_checkpoint_list_by_task(self):
        """测试：按任务列出快照"""
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_dir = os.path.join(tmpdir, "tasks")
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")

            tm = TaskManager(tasks_dir=tasks_dir)
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)
            scheduler = Scheduler(task_manager=tm)

            task1 = tm.create_task(name="任务1", domain="AT_支付域")
            task2 = tm.create_task(name="任务2", domain="DA_订单域")

            scheduler.assign_employee(task1.id, "dev_001")

            # 为task1保存多个快照
            for i in range(3):
                phase = scheduler.get_current_phase(task1.id)
                cm.save(
                    task_id=task1.id,
                    phase=phase.value,
                    task_state={"step": i},
                    execution_context={}
                )
                scheduler.advance_phase(task1.id)

            # 为task2保存一个快照（使用不同phase避免覆盖）
            cm.save(
                task_id=task2.id,
                phase="acceptance",  # 使用不同阶段
                task_state={},
                execution_context={}
            )

            # 列出task1的快照
            checkpoints = cm.list_checkpoints(task_id=task1.id)
            assert len(checkpoints) == 3

            # 列出task2的快照
            checkpoints2 = cm.list_checkpoints(task_id=task2.id)
            assert len(checkpoints2) == 1


class TestCheckpointPersistence:
    """快照持久化集成测试"""

    def test_checkpoint_persist_to_disk(self):
        """测试：快照持久化到磁盘"""
        from claudeflow.workflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            checkpoint = cm.save(
                task_id="task_001",
                phase="development",
                task_state={"progress": 80},
                execution_context={"file": "test.py"}
            )

            # 验证文件存在
            files = os.listdir(checkpoint_dir)
            assert len(files) > 0
            assert files[0].endswith(".json")

    def test_checkpoint_restore_from_disk(self):
        """测试：从磁盘恢复快照"""
        from claudeflow.workflow.checkpoint import CheckpointManager, Checkpoint

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 保存
            saved = cm.save(
                task_id="task_001",
                phase="testing",
                task_state={"status": "testing"},
                execution_context={"test_file": "test_x.py"}
            )

            # 创建新的Manager实例（模拟重启）
            cm2 = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 恢复
            restored = cm2.restore(filename=saved.filename)

            assert restored.task_id == "task_001"
            assert restored.phase == "testing"
            assert restored.task_state["status"] == "testing"