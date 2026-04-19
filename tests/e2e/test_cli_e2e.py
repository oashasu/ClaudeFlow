"""E2E测试 - CLI完整工作流端到端测试

测试真实用户场景的完整CLI操作流程
"""

import pytest
import tempfile
import os
import json


class TestE2eCliWorkflow:
    """CLI E2E工作流测试"""

    def test_e2e_task_create_list_show(self):
        """E2E测试：创建任务→列出任务→查看详情"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 1. 创建任务
            result = cli.run([
                "task", "create",
                "--name", "E2E测试任务",
                "--domain", "AT_支付域",
                "--priority", "高"
            ])

            assert result.success == True
            assert "任务创建成功" in result.stdout if hasattr(result, 'stdout') else result.output
            task_id = result.task_id

            # 2. 列出任务
            result = cli.run(["task", "list"])

            assert result.success == True
            assert "E2E测试任务" in result.output

            # 3. 查看任务详情
            result = cli.run(["task", "show", "--id", task_id])

            assert result.success == True
            assert "E2E测试任务" in result.output

    def test_e2e_status_all(self):
        """E2E测试：创建多个任务→查询全局状态"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建3个任务
            for i in range(3):
                result = cli.run([
                    "task", "create",
                    "--name", f"E2E任务{i+1}",
                    "--domain", "AT_支付域"
                ])
                assert result.success == True

            # 查询全局状态
            result = cli.run(["status", "--all"])

            assert result.success == True
            assert "任务总数: 3" in result.output

    def test_e2e_cli_error_handling(self):
        """E2E测试：错误处理"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 缺少必需参数
            result = cli.run(["task", "create", "--domain", "AT_支付域"])

            assert result.success == False

            # 查看不存在任务
            result = cli.run(["task", "show", "--id", "nonexistent"])

            assert result.success == False


class TestE2eTaskPersistence:
    """任务持久化E2E测试"""

    def test_e2e_task_persistence(self):
        """E2E测试：任务持久化验证"""
        from claudeflow.cli import CliApp

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = CliApp(tasks_dir=tmpdir)

            # 创建任务
            result = cli.run([
                "task", "create",
                "--name", "持久化测试",
                "--domain", "AT_支付域",
                "--description", "E2E持久化验证"
            ])

            assert result.success == True

            # 验证文件存在
            task_files = os.listdir(tmpdir)
            assert len(task_files) > 0

            # 验证文件内容
            task_file = os.path.join(tmpdir, task_files[0])
            with open(task_file, 'r') as f:
                data = json.load(f)

            # data可能是列表或字典
            if isinstance(data, list):
                data = data[0]

            assert data["name"] == "持久化测试"
            assert data["domain"] == "AT_支付域"


class TestE2eCheckpointPersistence:
    """Checkpoint持久化E2E测试"""

    def test_e2e_checkpoint_save_restore(self):
        """E2E测试：Checkpoint保存恢复"""
        from claudeflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_dir = os.path.join(tmpdir, "checkpoint")
            cm = CheckpointManager(checkpoint_dir=checkpoint_dir)

            # 保存快照
            checkpoint = cm.save(
                task_id="e2e_task_001",
                phase="development",
                task_state={"status": "running", "progress": 50},
                execution_context={"file": "main.py"}
            )

            assert checkpoint.checkpoint_id is not None

            # 验证文件存在
            checkpoint_files = os.listdir(checkpoint_dir)
            assert len(checkpoint_files) > 0

            # 恢复快照
            restored = cm.restore(checkpoint_id=checkpoint.checkpoint_id)

            assert restored.task_id == "e2e_task_001"
            assert restored.task_state["progress"] == 50


class TestE2eCompleteWorkflow:
    """完整工作流E2E测试"""

    def test_e2e_full_task_lifecycle(self):
        """E2E测试：任务完整生命周期"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.scheduler import Scheduler
        from claudeflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            # 创建任务
            task = tm.create_task(
                name="E2E完整流程",
                domain="AT_支付域",
                priority="高"
            )

            # 分配员工
            scheduler.assign_employee(task.id, "dev_001")

            # 推进阶段
            for _ in range(3):
                scheduler.advance_phase(task.id)

            # 完成任务
            scheduler.complete_task(task.id)

            # 验证最终状态
            final_task = tm.get_task(task.id)
            assert final_task.status == TaskStatus.COMPLETED.value

            # 验证员工释放
            assert scheduler.is_employee_available("dev_001")


class TestE2eSchedulerFlow:
    """调度器流程E2E测试"""

    def test_e2e_scheduler_phase_progression(self):
        """E2E测试：调度器阶段推进"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.scheduler import Scheduler
        from claudeflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="E2E阶段推进", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 验证初始阶段
            phase = scheduler.get_current_phase(task.id)
            assert phase == Phase.REQUIREMENTS

            # 推进所有阶段
            for expected_phase in [Phase.BRAINSTORM, Phase.ARCHITECTURE, Phase.DESIGN]:
                scheduler.advance_phase(task.id)
                phase = scheduler.get_current_phase(task.id)
                assert phase == expected_phase

    def test_e2e_scheduler_failure_recovery(self):
        """E2E测试：调度器失败恢复"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.scheduler import Scheduler
        from claudeflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="E2E失败恢复", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 模拟失败
            scheduler.handle_failure(task.id, "network_timeout")

            # 验证状态
            failed_task = tm.get_task(task.id)
            assert failed_task.status == TaskStatus.FAILED.value

            # 调度重试
            scheduler.schedule_retry(task.id)
            retrying_task = tm.get_task(task.id)
            assert retrying_task.status == TaskStatus.RETRYING.value

    def test_e2e_scheduler_progress_tracking(self):
        """E2E测试：调度器进度追踪"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.scheduler import Scheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="E2E进度追踪", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 初始进度
            progress = scheduler.get_progress(task.id)
            assert progress == 0

            # 推进阶段后进度更新
            scheduler.advance_phase(task.id)
            scheduler.advance_phase(task.id)
            scheduler.advance_phase(task.id)

            progress = scheduler.get_progress(task.id)
            assert progress > 0

    def test_e2e_scheduler_employee_management(self):
        """E2E测试：调度器员工管理"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.scheduler import Scheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            # 验证员工初始可用
            assert scheduler.is_employee_available("dev_001") == True
            assert scheduler.is_employee_available("dev_002") == True

            # 创建任务并分配
            task = tm.create_task(name="E2E员工管理", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 验证员工忙碌
            assert scheduler.is_employee_available("dev_001") == False
            assert scheduler.is_employee_available("dev_002") == True

            # 完成任务
            scheduler.complete_task(task.id)

            # 验证员工释放
            assert scheduler.is_employee_available("dev_001") == True