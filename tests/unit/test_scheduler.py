"""流程调度模块单元测试

调度核心：员工分配、阶段推进、失败处理、重试调度
"""

import pytest
import tempfile
from datetime import datetime


class TestEmployeeAssignment:
    """员工分配测试"""

    def test_assign_employee_to_task(self):
        """测试：给任务分配员工"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="分配测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            updated = tm.get_task(task.id)
            assert updated.assigned_employee == "dev_001"
            assert updated.status == TaskStatus.RUNNING.value

    def test_assign_employee_changes_status_to_running(self):
        """测试：分配员工后状态变为执行中"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="状态测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            updated = tm.get_task(task.id)
            assert updated.status == TaskStatus.RUNNING.value


class TestPhaseProgress:
    """阶段推进测试"""

    def test_get_current_phase(self):
        """测试：获取当前阶段"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="阶段测试", domain="AT_支付域")
            phase = scheduler.get_current_phase(task.id)

            assert phase == Phase.REQUIREMENTS

    def test_advance_phase(self):
        """测试：推进到下一阶段"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="推进测试", domain="AT_支付域")
            scheduler.advance_phase(task.id)

            phase = scheduler.get_current_phase(task.id)
            assert phase == Phase.BRAINSTORM

    def test_advance_to_final_phase(self):
        """测试：推进到最终阶段"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="最终阶段", domain="AT_支付域")

            # 推进7次到验收阶段
            for _ in range(7):
                scheduler.advance_phase(task.id)

            phase = scheduler.get_current_phase(task.id)
            assert phase == Phase.ACCEPTANCE

    def test_advance_phase_updates_progress(self):
        """测试：推进阶段更新进度"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="进度测试", domain="AT_支付域")
            progress = scheduler.get_progress(task.id)
            assert progress == 0  # 0%

            scheduler.advance_phase(task.id)
            progress = scheduler.get_progress(task.id)
            assert progress == 12  # 1/8 ≈ 12%


class TestFailureHandling:
    """失败处理测试"""

    def test_handle_task_failure(self):
        """测试：处理任务失败"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="失败测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            scheduler.handle_failure(task.id, error_type="network_timeout")

            updated = tm.get_task(task.id)
            assert updated.status == TaskStatus.FAILED.value

    def test_handle_failure_records_error(self):
        """测试：记录失败错误信息"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="错误记录", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            scheduler.handle_failure(
                task.id,
                error_type="network_timeout",
                error_message="API连接超时"
            )

            task_ctx = scheduler.get_task_context(task.id)
            assert task_ctx["last_error_type"] == "network_timeout"
            assert task_ctx["last_error_message"] == "API连接超时"


class TestRetryScheduling:
    """重试调度测试"""

    def test_schedule_retry_for_retriable_error(self):
        """测试：可重试错误触发重试"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="重试测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            scheduler.handle_failure(task.id, error_type="network_timeout")
            scheduler.schedule_retry(task.id)

            updated = tm.get_task(task.id)
            assert updated.status == TaskStatus.RETRYING.value

    def test_retry_count_increment(self):
        """测试：重试次数递增"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="次数递增", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            scheduler.handle_failure(task.id, error_type="network_timeout")
            scheduler.schedule_retry(task.id)

            task_ctx = scheduler.get_task_context(task.id)
            assert task_ctx["retry_count"] == 1

    def test_no_retry_for_non_retriable_error(self):
        """测试：不可重试错误不触发重试"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="不重试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            scheduler.handle_failure(task.id, error_type="permission_denied")
            scheduler.schedule_retry(task.id)

            # 应该进入人工介入而非重试
            updated = tm.get_task(task.id)
            assert updated.status == TaskStatus.HUMAN_INTERVENTION.value


class TestTaskCompletion:
    """任务完成测试"""

    def test_complete_task_success(self):
        """测试：任务成功完成"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="完成测试", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            scheduler.complete_task(task.id)

            updated = tm.get_task(task.id)
            assert updated.status == TaskStatus.COMPLETED.value

    def test_complete_task_releases_employee(self):
        """测试：完成任务释放员工"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="释放员工", domain="AT_支付域")
            scheduler.assign_employee(task.id, "dev_001")

            scheduler.complete_task(task.id)

            # 员工应该被释放
            assert scheduler.is_employee_available("dev_001")


class TestSchedulerContext:
    """调度上下文测试"""

    def test_scheduler_has_task_context(self):
        """测试：调度器维护任务上下文"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="上下文", domain="AT_支付域")

            task_ctx = scheduler.get_task_context(task.id)
            assert task_ctx is not None
            assert "retry_count" in task_ctx

    def test_scheduler_context_tracks_phase(self):
        """测试：上下文跟踪阶段"""
        from claudflow.scheduler import Scheduler
        from claudflow.task_manager import TaskManager
        from claudflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="跟踪阶段", domain="AT_支付域")

            task_ctx = scheduler.get_task_context(task.id)
            assert task_ctx["current_phase"] == Phase.REQUIREMENTS.value