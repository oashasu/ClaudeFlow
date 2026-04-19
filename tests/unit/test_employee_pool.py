"""动态员工池模块单元测试

三层池结构：活跃池、休眠池、增长池
"""

import pytest
import tempfile


class TestEmployeePoolBasics:
    """员工池基础功能测试"""

    def test_create_employee_pool(self):
        """测试：创建员工池"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        assert pool is not None

    def test_add_employee_to_active_pool(self):
        """测试：添加员工到活跃池"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        employee_id = pool.add_employee(
            role="developer",
            domains=["AT_支付域"]
        )

        assert employee_id is not None
        assert employee_id.startswith("employee_")

    def test_employee_has_attributes(self):
        """测试：员工具有属性"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        employee_id = pool.add_employee(
            role="developer",
            domains=["AT_支付域"],
            model="sonnet"
        )

        employee = pool.get_employee(employee_id)
        assert employee.role == "developer"
        assert employee.domains == ["AT_支付域"]
        assert employee.model == "sonnet"


class TestThreePoolStructure:
    """三层池结构测试"""

    def test_active_pool_contains_working_employees(self):
        """测试：活跃池包含正在工作的员工"""
        from claudeflow.employee_pool import EmployeePool, EmployeeStatus

        pool = EmployeePool()
        employee_id = pool.add_employee(role="developer", domains=["AT_支付域"])

        status = pool.get_employee_status(employee_id)
        assert status == EmployeeStatus.IDLE  # 新员工默认闲置

    def test_employee_status_changes_to_busy(self):
        """测试：分配任务后状态变为忙碌"""
        from claudeflow.employee_pool import EmployeePool, EmployeeStatus

        pool = EmployeePool()
        employee_id = pool.add_employee(role="developer", domains=["AT_支付域"])

        pool.assign_task(employee_id, "task_001")

        status = pool.get_employee_status(employee_id)
        assert status == EmployeeStatus.BUSY

    def test_employee_moves_to_sleep_pool(self):
        """测试：员工进入休眠池"""
        from claudeflow.employee_pool import EmployeePool, EmployeeStatus

        pool = EmployeePool()
        employee_id = pool.add_employee(role="developer", domains=["AT_支付域"])

        pool.put_to_sleep(employee_id)

        status = pool.get_employee_status(employee_id)
        assert status == EmployeeStatus.SLEEPING

    def test_wake_employee_from_sleep_pool(self):
        """测试：从休眠池唤醒员工"""
        from claudeflow.employee_pool import EmployeePool, EmployeeStatus

        pool = EmployeePool()
        employee_id = pool.add_employee(role="developer", domains=["AT_支付域"])

        pool.put_to_sleep(employee_id)
        pool.wake_up(employee_id)

        status = pool.get_employee_status(employee_id)
        assert status == EmployeeStatus.IDLE

    def test_remove_employee_from_pool(self):
        """测试：从池中移除员工"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        employee_id = pool.add_employee(role="developer", domains=["AT_支付域"])

        pool.remove_employee(employee_id)

        employee = pool.get_employee(employee_id)
        assert employee is None


class TestDomainMatching:
    """领域匹配测试"""

    def test_find_employee_by_domain(self):
        """测试：根据领域查找员工"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        pool.add_employee(role="developer", domains=["AT_支付域"])
        pool.add_employee(role="developer", domains=["DA_订单域"])

        employee = pool.find_employee_by_domain("AT_支付域")
        assert employee is not None
        assert "AT_支付域" in employee.domains

    def test_find_idle_employee_by_domain(self):
        """测试：根据领域查找闲置员工"""
        from claudeflow.employee_pool import EmployeePool, EmployeeStatus

        pool = EmployeePool()
        emp1 = pool.add_employee(role="developer", domains=["AT_支付域"])
        emp2 = pool.add_employee(role="developer", domains=["AT_支付域"])

        # 第一个员工忙碌
        pool.assign_task(emp1, "task_001")

        # 查找AT_支付域的闲置员工
        employee = pool.find_idle_employee_by_domain("AT_支付域")
        assert employee is not None
        assert employee.id == emp2

    def test_no_matching_employee_returns_none(self):
        """测试：没有匹配员工返回None"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        pool.add_employee(role="developer", domains=["AT_支付域"])

        employee = pool.find_employee_by_domain("FM_会员域")
        assert employee is None


class TestPoolStatistics:
    """池统计测试"""

    def test_get_active_pool_size(self):
        """测试：获取活跃池大小"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        pool.add_employee(role="developer", domains=["AT_支付域"])
        pool.add_employee(role="developer", domains=["DA_订单域"])

        size = pool.get_active_pool_size()
        assert size == 2

    def test_get_sleep_pool_size(self):
        """测试：获取休眠池大小"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        emp1 = pool.add_employee(role="developer", domains=["AT_支付域"])
        emp2 = pool.add_employee(role="developer", domains=["DA_订单域"])

        pool.put_to_sleep(emp1)
        pool.put_to_sleep(emp2)

        size = pool.get_sleep_pool_size()
        assert size == 2

    def test_get_busy_count(self):
        """测试：获取忙碌员工数量"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        emp1 = pool.add_employee(role="developer", domains=["AT_支付域"])
        emp2 = pool.add_employee(role="developer", domains=["DA_订单域"])

        pool.assign_task(emp1, "task_001")

        count = pool.get_busy_count()
        assert count == 1

    def test_get_idle_count(self):
        """测试：获取闲置员工数量"""
        from claudeflow.employee_pool import EmployeePool

        pool = EmployeePool()
        emp1 = pool.add_employee(role="developer", domains=["AT_支付域"])
        emp2 = pool.add_employee(role="developer", domains=["DA_订单域"])

        pool.assign_task(emp1, "task_001")

        count = pool.get_idle_count()
        assert count == 1