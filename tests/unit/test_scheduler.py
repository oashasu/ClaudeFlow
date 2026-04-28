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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import TaskStatus

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import TaskStatus

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="阶段测试", domain="AT_支付域")
            phase = scheduler.get_current_phase(task.id)

            assert phase == Phase.REQUIREMENTS

    def test_advance_phase(self):
        """测试：推进到下一阶段"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="推进测试", domain="AT_支付域")
            scheduler.advance_phase(task.id)

            phase = scheduler.get_current_phase(task.id)
            assert phase == Phase.BRAINSTORM

    def test_advance_to_final_phase(self):
        """测试：推进到最终阶段"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import Phase

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import TaskStatus

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import TaskStatus

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import TaskStatus

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import TaskStatus

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

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
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="上下文", domain="AT_支付域")

            task_ctx = scheduler.get_task_context(task.id)
            assert task_ctx is not None
            assert "retry_count" in task_ctx

    def test_scheduler_context_tracks_phase(self):
        """测试：上下文跟踪阶段"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.workflow.state_machine import Phase

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="跟踪阶段", domain="AT_支付域")

            task_ctx = scheduler.get_task_context(task.id)
            assert task_ctx["current_phase"] == Phase.REQUIREMENTS.value


class TestSessionLifecycle:
    """Session生命周期管理测试（V2新增）"""

    def test_create_session_for_task(self):
        """测试：为任务创建Session"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="Session测试", domain="AT_支付域")
            session_id = scheduler.create_session(task.id)

            assert session_id is not None
            assert session_id.startswith("session_")

    def test_session_linked_to_task(self):
        """测试：Session关联到任务"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="Session关联", domain="AT_支付域")
            session_id = scheduler.create_session(task.id)

            # 任务应该有session_id
            updated = tm.get_task(task.id)
            assert updated.session_id == session_id

    def test_get_session_state(self):
        """测试：获取Session状态"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="Session状态", domain="AT_支付域")
            session_id = scheduler.create_session(task.id)

            state = scheduler.get_session_state(session_id)
            assert state == "running"

    def test_end_session(self):
        """测试：结束Session"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="结束Session", domain="AT_支付域")
            session_id = scheduler.create_session(task.id)

            scheduler.end_session(session_id)

            state = scheduler.get_session_state(session_id)
            assert state == "completed"

    def test_get_session_by_task(self):
        """测试：通过任务获取Session"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="获取Session", domain="AT_支付域")
            session_id = scheduler.create_session(task.id)

            retrieved = scheduler.get_session_by_task(task.id)
            assert retrieved == session_id

    def test_multiple_sessions_for_different_tasks(self):
        """测试：不同任务有不同Session"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task1 = tm.create_task(name="任务1", domain="AT_支付域")
            task2 = tm.create_task(name="任务2", domain="AT_支付域")

            session1 = scheduler.create_session(task1.id)
            session2 = scheduler.create_session(task2.id)

            assert session1 != session2


class TestSubtaskDetection:
    """子任务检测测试（V2.1.0新增）"""

    def test_detect_explicit_marker(self):
        """测试：检测显式完成标记"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.subtask_detector import CompletionType

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="标记检测", domain="AT_支付域")

            output = "工作已完成\n# SUBTASK_COMPLETE"
            is_complete, prompt = scheduler.detect_and_handle_completion(
                task.id, output
            )

            assert is_complete is True
            assert prompt is not None
            assert "总结本阶段工作" in prompt

    def test_detect_tests_passed(self):
        """测试：检测pytest测试通过"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager
        from claudeflow.subtask_detector import CompletionType

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="测试检测", domain="AT_支付域")

            output = "运行pytest结果：\n5 passed, 0 failed"
            is_complete, prompt = scheduler.detect_and_handle_completion(
                task.id, output
            )

            assert is_complete is True
            assert prompt is not None

    def test_detect_not_complete(self):
        """测试：未完成情况不触发"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="未完成", domain="AT_支付域")

            output = "正在进行开发..."
            is_complete, prompt = scheduler.detect_and_handle_completion(
                task.id, output
            )

            assert is_complete is False
            assert prompt is None

    def test_completion_type_recorded_in_context(self):
        """测试：完成类型记录到上下文"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="上下文记录", domain="AT_支付域")

            output = "# SUBTASK_COMPLETE"
            scheduler.detect_and_handle_completion(task.id, output)

            ctx = scheduler.get_task_context(task.id)
            assert ctx["last_completion_type"] == "explicit_marker"


class TestQualityCheck:
    """质量检查测试（V2.1.0新增）"""

    def test_parse_quality_score(self):
        """测试：解析质量评分"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            output = "总结完成\n自评质量（1-10分）：8"
            score, doubt = scheduler.parse_quality_check(output)

            assert score == 8
            assert doubt is False

    def test_parse_doubt_flag_yes(self):
        """测试：解析疑虑标记（是）"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            output = "总结完成\n是否有疑虑需人工确认？（是/否）：是"
            score, doubt = scheduler.parse_quality_check(output)

            assert doubt is True

    def test_parse_doubt_flag_no(self):
        """测试：解析疑虑标记（否）"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            output = "总结完成\n是否有疑虑需人工确认？（是/否）：否"
            score, doubt = scheduler.parse_quality_check(output)

            assert doubt is False

    def test_should_pause_on_doubt(self):
        """测试：疑虑标记触发暂停"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(
                name="暂停测试",
                domain="AT_支付域",
                pause_on_doubt=True
            )
            scheduler.update_quality_metrics(task.id, 7, True)

            should_pause = scheduler.should_pause_for_review(task.id)
            assert should_pause is True

    def test_should_pause_on_low_score(self):
        """测试：低评分触发暂停"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="低分暂停", domain="AT_支付域")
            scheduler.update_quality_metrics(task.id, 3, False)

            should_pause = scheduler.should_pause_for_review(task.id)
            assert should_pause is True

    def test_should_not_pause_on_high_score(self):
        """测试：高评分不暂停"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="高分不暂停", domain="AT_支付域")
            scheduler.update_quality_metrics(task.id, 8, False)

            should_pause = scheduler.should_pause_for_review(task.id)
            assert should_pause is False

    def test_update_quality_metrics(self):
        """测试：更新质量指标"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="质量更新", domain="AT_支付域")
            scheduler.update_quality_metrics(task.id, 9, False)

            updated = tm.get_task(task.id)
            assert updated.quality_score == 9
            assert updated.doubt_flag is False

    def test_clear_subtask_state(self):
        """测试：清除子任务状态"""
        from claudeflow.workflow.scheduler import Scheduler
        from claudeflow.workflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)
            scheduler = Scheduler(task_manager=tm)

            task = tm.create_task(name="清除状态", domain="AT_支付域")

            # 先设置完成状态
            output = "# SUBTASK_COMPLETE"
            scheduler.detect_and_handle_completion(task.id, output)

            # 清除状态
            scheduler.clear_subtask_state(task.id)

            ctx = scheduler.get_task_context(task.id)
            assert "last_completion_type" not in ctx