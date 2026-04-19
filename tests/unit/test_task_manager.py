"""任务管理模块单元测试

任务CRUD：创建、查询、更新、删除
"""

import pytest
import tempfile
import os
from datetime import datetime


class TestTaskCreation:
    """任务创建测试"""

    def test_create_task_success(self):
        """测试：正常创建任务"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(
                name="测试任务",
                domain="AT_支付域",
                priority="高"
            )

            assert task.id is not None
            assert task.name == "测试任务"
            assert task.domain == "AT_支付域"
            assert task.status == "pending"  # status是字符串值

    def test_create_task_with_description(self):
        """测试：创建带描述的任务"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(
                name="修复bug",
                domain="AT_支付域",
                description="退款手续费计算错误"
            )

            assert task.description == "退款手续费计算错误"

    def test_create_task_generates_task_dir(self):
        """测试：创建任务时生成目录结构"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(name="测试任务", domain="AT_支付域")

            # 验证目录存在
            task_dir = os.path.join(tmpdir, task.task_dir_name)
            assert os.path.exists(task_dir)

    def test_create_task_duplicate_name_adds_suffix(self):
        """测试：任务名称重复时自动添加后缀"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task1 = tm.create_task(name="测试任务", domain="AT_支付域")
            task2 = tm.create_task(name="测试任务", domain="AT_支付域")

            assert task1.name != task2.name


class TestTaskQuery:
    """任务查询测试"""

    def test_get_task_by_id(self):
        """测试：按ID查询任务"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            created = tm.create_task(name="查询测试", domain="AT_支付域")
            found = tm.get_task(created.id)

            assert found.id == created.id
            assert found.name == "查询测试"

    def test_get_task_not_found_raises_error(self):
        """测试：查询不存在任务抛出错误"""
        from claudeflow.task_manager import TaskManager, TaskNotFoundError

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            with pytest.raises(TaskNotFoundError):
                tm.get_task("non_existent_id")

    def test_list_tasks_empty(self):
        """测试：空任务列表"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            tasks = tm.list_tasks()
            assert tasks == []

    def test_list_tasks_with_filter(self):
        """测试：按状态过滤任务列表"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            tm.create_task(name="任务1", domain="AT_支付域")
            tm.create_task(name="任务2", domain="DA_订单域")

            tasks = tm.list_tasks(status=TaskStatus.PENDING)
            assert len(tasks) == 2

    def test_list_tasks_with_limit(self):
        """测试：任务列表限制数量"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            for i in range(5):
                tm.create_task(name=f"任务{i}", domain="AT_支付域")

            tasks = tm.list_tasks(limit=3)
            assert len(tasks) == 3


class TestTaskUpdate:
    """任务更新测试"""

    def test_update_task_status(self):
        """测试：更新任务状态"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(name="状态更新", domain="AT_支付域")
            updated = tm.update_task(task.id, status=TaskStatus.RUNNING)

            assert updated.status == TaskStatus.RUNNING.value  # status是字符串

    def test_update_task_priority(self):
        """测试：更新任务优先级"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(name="优先级更新", domain="AT_支付域", priority="中")
            updated = tm.update_task(task.id, priority="高")

            assert updated.priority == "高"

    def test_update_task_assigned_employee(self):
        """测试：更新任务分配员工"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(name="分配员工", domain="AT_支付域")
            updated = tm.update_task(task.id, assigned_employee="dev_001")

            assert updated.assigned_employee == "dev_001"


class TestTaskDelete:
    """任务删除测试"""

    def test_cancel_task(self):
        """测试：取消任务"""
        from claudeflow.task_manager import TaskManager
        from claudeflow.state_machine import TaskStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(name="取消测试", domain="AT_支付域")
            tm.cancel_task(task.id, reason="需求变更")

            found = tm.get_task(task.id)
            assert found.status == TaskStatus.ARCHIVED.value  # status是字符串

    def test_cancel_task_with_reason(self):
        """测试：取消任务记录原因"""
        from claudeflow.task_manager import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            tm = TaskManager(tasks_dir=tmpdir)

            task = tm.create_task(name="取消原因", domain="AT_支付域")
            tm.cancel_task(task.id, reason="测试取消")

            found = tm.get_task(task.id)
            assert found.cancel_reason == "测试取消"


class TestTaskData:
    """任务数据结构测试"""

    def test_task_has_required_fields(self):
        """测试：任务包含必需字段"""
        from claudeflow.task_manager import Task

        task = Task(
            id="task_001",
            name="测试",
            domain="AT_支付域",
            status="pending",
            priority="中",
            created_at=datetime.now(),
            task_dir_name="2026-04-19_测试"
        )

        assert hasattr(task, "id")
        assert hasattr(task, "name")
        assert hasattr(task, "domain")
        assert hasattr(task, "status")
        assert hasattr(task, "priority")
        assert hasattr(task, "created_at")
        assert hasattr(task, "task_dir_name")

    def test_task_to_dict(self):
        """测试：任务序列化为字典"""
        from claudeflow.task_manager import Task

        task = Task(
            id="task_001",
            name="测试",
            domain="AT_支付域",
            status="pending",
            priority="中",
            created_at=datetime.now(),
            task_dir_name="2026-04-19_测试"
        )

        data = task.to_dict()
        assert data["id"] == "task_001"
        assert data["name"] == "测试"

    def test_task_from_dict(self):
        """测试：从字典反序列化任务"""
        from claudeflow.task_manager import Task

        data = {
            "id": "task_001",
            "name": "测试",
            "domain": "AT_支付域",
            "status": "pending",
            "priority": "中",
            "created_at": "2026-04-19T10:00:00",
            "task_dir_name": "2026-04-19_测试"
        }

        task = Task.from_dict(data)
        assert task.id == "task_001"
        assert task.name == "测试"