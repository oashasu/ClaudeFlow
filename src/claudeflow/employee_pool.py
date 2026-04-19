"""动态员工池模块 - 三层池结构

V1核心功能：活跃池、休眠池、增长池
"""

import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class EmployeeStatus(Enum):
    """员工状态枚举"""
    IDLE = "idle"      # 闲置，等待任务
    BUSY = "busy"      # 执行中，正在处理任务
    SLEEPING = "sleeping"  # 休眠，暂时不工作


class EmployeeRole(Enum):
    """员工角色枚举"""
    ANALYST = "analyst"      # 分析师
    ARCHITECT = "architect"  # 架构师
    DEVELOPER = "developer"  # 开发员
    TESTER = "tester"        # 测试员
    REVIEWER = "reviewer"    # 审查员


@dataclass
class Employee:
    """员工数据模型"""
    id: str
    role: str
    domains: List[str] = field(default_factory=list)
    model: str = "sonnet"
    status: EmployeeStatus = EmployeeStatus.IDLE
    current_task: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()


class EmployeePool:
    """动态员工池"""

    def __init__(self):
        """初始化员工池"""
        self._active_pool: Dict[str, Employee] = {}
        self._sleep_pool: Dict[str, Employee] = {}

    def add_employee(
        self,
        role: str,
        domains: List[str],
        model: str = "sonnet"
    ) -> str:
        """
        添加员工到活跃池

        Args:
            role: 员工角色
            domains: 熟悉领域列表
            model: 推荐模型

        Returns:
            员工ID
        """
        employee_id = f"employee_{uuid.uuid4().hex[:8]}"

        employee = Employee(
            id=employee_id,
            role=role,
            domains=domains,
            model=model,
            status=EmployeeStatus.IDLE
        )

        self._active_pool[employee_id] = employee
        return employee_id

    def get_employee(self, employee_id: str) -> Optional[Employee]:
        """
        获取员工信息

        Args:
            employee_id: 员工ID

        Returns:
            员工对象，不存在返回None
        """
        # 先查活跃池
        if employee_id in self._active_pool:
            return self._active_pool[employee_id]
        # 再查休眠池
        if employee_id in self._sleep_pool:
            return self._sleep_pool[employee_id]
        return None

    def get_employee_status(self, employee_id: str) -> EmployeeStatus:
        """
        获取员工状态

        Args:
            employee_id: 员工ID

        Returns:
            员工状态
        """
        employee = self.get_employee(employee_id)
        if employee:
            return employee.status
        return EmployeeStatus.IDLE

    def assign_task(self, employee_id: str, task_id: str):
        """
        分配任务给员工

        Args:
            employee_id: 员工ID
            task_id: 任务ID
        """
        employee = self.get_employee(employee_id)
        if employee:
            employee.status = EmployeeStatus.BUSY
            employee.current_task = task_id

    def release_task(self, employee_id: str):
        """
        释放员工任务

        Args:
            employee_id: 员工ID
        """
        employee = self.get_employee(employee_id)
        if employee:
            employee.status = EmployeeStatus.IDLE
            employee.current_task = None

    def put_to_sleep(self, employee_id: str):
        """
        将员工移入休眠池

        Args:
            employee_id: 员工ID
        """
        if employee_id in self._active_pool:
            employee = self._active_pool.pop(employee_id)
            employee.status = EmployeeStatus.SLEEPING
            self._sleep_pool[employee_id] = employee

    def wake_up(self, employee_id: str):
        """
        从休眠池唤醒员工

        Args:
            employee_id: 员工ID
        """
        if employee_id in self._sleep_pool:
            employee = self._sleep_pool.pop(employee_id)
            employee.status = EmployeeStatus.IDLE
            self._active_pool[employee_id] = employee

    def remove_employee(self, employee_id: str):
        """
        从池中移除员工

        Args:
            employee_id: 员工ID
        """
        self._active_pool.pop(employee_id, None)
        self._sleep_pool.pop(employee_id, None)

    def find_employee_by_domain(self, domain: str) -> Optional[Employee]:
        """
        根据领域查找员工

        Args:
            domain: 业务领域

        Returns:
            匹配的员工，不存在返回None
        """
        for employee in self._active_pool.values():
            if domain in employee.domains:
                return employee
        for employee in self._sleep_pool.values():
            if domain in employee.domains:
                return employee
        return None

    def find_idle_employee_by_domain(self, domain: str) -> Optional[Employee]:
        """
        根据领域查找闲置员工

        Args:
            domain: 业务领域

        Returns:
            匹配的闲置员工，不存在返回None
        """
        for employee in self._active_pool.values():
            if domain in employee.domains and employee.status == EmployeeStatus.IDLE:
                return employee
        return None

    def get_active_pool_size(self) -> int:
        """获取活跃池大小"""
        return len(self._active_pool)

    def get_sleep_pool_size(self) -> int:
        """获取休眠池大小"""
        return len(self._sleep_pool)

    def get_busy_count(self) -> int:
        """获取忙碌员工数量"""
        return sum(
            1 for e in self._active_pool.values()
            if e.status == EmployeeStatus.BUSY
        )

    def get_idle_count(self) -> int:
        """获取闲置员工数量"""
        return sum(
            1 for e in self._active_pool.values()
            if e.status == EmployeeStatus.IDLE
        )