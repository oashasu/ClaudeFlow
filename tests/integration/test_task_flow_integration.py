"""集成测试 - 任务流程完整生命周期

测试 TaskManager + Scheduler + StateMachine 协作
"""

import pytest
import tempfile
import os


class TestTaskFlowIntegration:
    """任务流程集成测试"""

    def test_task_full_lifecycle(self):
        """测试：任务完整生命周期"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            # 1. 创建任务
            task = tm.create_task(
                name="集成测试任务",
                domain="AT_支付域",
                priority="高"
            )
            assert task.status == TaskStatus.PENDING.value

            # 2. 分配员工
            scheduler.assign_employee(task.id, "dev_001")
            updated = tm.get_task(task.id)
            assert updated.status == TaskStatus.RUNNING.value
            assert updated.assigned_employee == "dev_001"

            # 3. 推进阶段
            scheduler.advance_phase(task.id)
            ctx = scheduler.get_task_context(task.id)
            assert ctx["current_phase"] == 2  # BRAINSTORM

            # 4. 完成任务
            scheduler.complete_task(task.id)
            completed = tm.get_task(task.id)
            assert completed.status == TaskStatus.COMPLETED.value
            assert scheduler.is_employee_available("dev_001")

    def test_task_failure_and_retry_flow(self):
        """测试：任务失败重试流程"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            # 创建并分配任务
            task = tm.create_task(name="失败测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 模拟失败（使用可重试错误类型）
            scheduler.handle_failure(task.id, "network_timeout", "网络超时")

            # 调度重试
            scheduler.schedule_retry(task.id)
            retrying = tm.get_task(task.id)
            assert retrying.status == TaskStatus.RETRYING.value

            # 检查重试次数
            ctx = scheduler.get_task_context(task.id)
            assert ctx["retry_count"] == 1
            assert ctx["last_error_type"] == "network_timeout"

    def test_task_max_retry_to_human_intervention(self):
        """测试：超过重试上限进入人工介入"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            # 创建任务
            task = tm.create_task(name="超重试测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 模拟3次失败和重试（使用可重试错误类型）
            for i in range(3):
                scheduler.handle_failure(task.id, "network_timeout")
                scheduler.schedule_retry(task.id)

            # 第4次失败
            scheduler.handle_failure(task.id, "network_timeout")
            scheduler.schedule_retry(task.id)

            # 应该进入人工介入
            final = tm.get_task(task.id)
            assert final.status == TaskStatus.HUMAN_INTERVENTION.value
            assert scheduler.is_employee_available("dev_001")

    def test_task_non_retriable_to_human_intervention(self):
        """测试：不可重试错误直接人工介入"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            # 创建任务
            task = tm.create_task(name="不可重试测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 模拟不可重试错误
            scheduler.handle_failure(task.id, "auth_error")
            scheduler.schedule_retry(task.id)

            # 应该直接进入人工介入
            final = tm.get_task(task.id)
            assert final.status == TaskStatus.HUMAN_INTERVENTION.value

    def test_multiple_tasks_concurrent_execution(self):
        """测试：多个任务并发执行"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            # 创建多个任务
            task1 = tm.create_task(name="任务1", domain="AT_支付域")
            task2 = tm.create_task(name="任务2", domain="DA_订单域")
            task3 = tm.create_task(name="任务3", domain="RA_报表域")

            # 分配不同员工
            scheduler.assign_employee(task1.id, "dev_001")
            scheduler.assign_employee(task2.id, "dev_002")
            scheduler.assign_employee(task3.id, "dev_003")

            # 验证状态
            assert scheduler.is_employee_available("dev_001") == False
            assert scheduler.is_employee_available("dev_002") == False
            assert scheduler.is_employee_available("dev_003") == False

            # 完成任务1
            scheduler.complete_task(task1.id)
            assert scheduler.is_employee_available("dev_001") == True

            # 完成任务2和3
            scheduler.complete_task(task2.id)
            scheduler.complete_task(task3.id)

            # 验证所有任务完成
            tasks = tm.list_tasks(status=TaskStatus.COMPLETED)
            assert len(tasks) == 3


class TestTaskProgressIntegration:
    """任务进度集成测试"""

    def test_phase_progress_tracking(self):
        """测试：阶段进度追踪"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="进度测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 初始进度
            progress = scheduler.get_progress(task.id)
            assert progress == 0

            # 推进多个阶段
            scheduler.advance_phase(task.id)
            scheduler.advance_phase(task.id)
            scheduler.advance_phase(task.id)

            progress = scheduler.get_progress(task.id)
            assert progress > 0

    def test_phase_history_recording(self):
        """测试：阶段历史记录"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler
        from claudflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="历史测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 推进阶段
            scheduler.advance_phase(task.id)
            scheduler.advance_phase(task.id)

            ctx = scheduler.get_task_context(task.id)
            history = ctx["phase_history"]

            assert len(history) == 2
            assert history[0]["phase"] == Phase.REQUIREMENTS.value


class TestTaskCancelIntegration:
    """任务取消集成测试"""

    def test_cancel_running_task(self):
        """测试：取消执行中任务"""
        from claudflow.task_manager import TaskManager
        from claudflow.scheduler import Scheduler
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="取消测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            # 取消任务
            tm.cancel_task(task.id, reason="用户请求取消")

            cancelled = tm.get_task(task.id)
            assert cancelled.status == TaskStatus.ARCHIVED.value
            assert cancelled.cancel_reason == "用户请求取消"