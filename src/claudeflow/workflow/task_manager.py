"""任务管理模块 - 任务CRUD操作

V1核心功能：任务创建、查询、更新、取消
V2新增功能：alert_handler告警支持、session_id字段、文件损坏告警
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from claudeflow.alert_handler import AlertHandler

from claudeflow.workflow.state_machine import TaskStatus


@dataclass
class Task:
    """任务数据模型"""

    id: str
    name: str
    domain: str
    status: str
    priority: str
    created_at: datetime
    task_dir_name: str
    description: Optional[str] = None
    assigned_employee: Optional[str] = None
    cancel_reason: Optional[str] = None
    session_id: Optional[str] = None  # V2新增
    pause_on_doubt: bool = False  # V2.1.0新增：质量检查有问题时是否暂停
    quality_score: Optional[int] = None  # V2.1.0新增：阶段质量评分
    doubt_flag: bool = False  # V2.1.0新增：是否有疑虑需人工确认

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """从字典反序列化"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class TaskNotFoundError(Exception):
    """任务不存在错误"""
    pass


class TaskManager:
    """任务管理器"""

    def __init__(self, tasks_dir: str, alert_handler: Optional["AlertHandler"] = None):
        """
        初始化任务管理器

        Args:
            tasks_dir: 任务存储目录
            alert_handler: 告警处理器（V2新增，用于文件损坏告警）
        """
        self.tasks_dir = tasks_dir
        self.tasks_file = os.path.join(tasks_dir, "tasks.json")
        self.alert_handler = alert_handler  # V2新增
        self._tasks: Dict[str, Task] = {}
        self._load_tasks()

    def _load_tasks(self):
        """加载任务数据"""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data:
                        task = Task.from_dict(task_data)
                        self._tasks[task.id] = task
            except json.JSONDecodeError as e:
                # V2新增：发送文件损坏告警
                if self.alert_handler:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(
                            self.alert_handler.send_file_corrupt_alert(
                                file_path=self.tasks_file,
                                error_type="JSONDecodeError",
                                module="task_manager"
                            )
                        )
                    except RuntimeError:
                        pass
                # 静默忽略，初始化为空任务列表

    def _save_tasks(self):
        """保存任务数据"""
        data = [task.to_dict() for task in self._tasks.values()]
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _generate_task_id(self) -> str:
        """生成任务ID"""
        return f"task_{uuid.uuid4().hex[:8]}"

    def _generate_task_dir_name(self, name: str) -> str:
        """生成任务目录名"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{date_str}_{name}"

    def _get_unique_name(self, name: str) -> str:
        """获取唯一任务名"""
        existing_names = {t.name for t in self._tasks.values()}
        if name not in existing_names:
            return name

        # 添加时间后缀
        suffix = datetime.now().strftime("%H%M%S")
        return f"{name}_{suffix}"

    def create_task(
        self,
        name: str,
        domain: str,
        priority: str = "中",
        description: Optional[str] = None,
        pause_on_doubt: bool = False  # V2.1.0新增
    ) -> Task:
        """
        创建任务

        Args:
            name: 任务名称
            domain: 所属领域
            priority: 优先级
            description: 任务描述
            pause_on_doubt: 质疑时是否暂停（V2.1.0新增）

        Returns:
            创建的任务对象
        """
        unique_name = self._get_unique_name(name)
        task_id = self._generate_task_id()
        task_dir_name = self._generate_task_dir_name(unique_name)

        task = Task(
            id=task_id,
            name=unique_name,
            domain=domain,
            status=TaskStatus.PENDING.value,
            priority=priority,
            created_at=datetime.now(),
            task_dir_name=task_dir_name,
            description=description,
            pause_on_doubt=pause_on_doubt  # V2.1.0新增
        )

        # 创建任务目录
        task_dir = os.path.join(self.tasks_dir, task_dir_name)
        os.makedirs(task_dir, exist_ok=True)

        # 保存任务
        self._tasks[task_id] = task
        self._save_tasks()

        return task

    def get_task(self, task_id: str) -> Task:
        """
        查询任务

        Args:
            task_id: 任务ID

        Returns:
            任务对象

        Raises:
            TaskNotFoundError: 任务不存在
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"任务不存在: {task_id}")
        return self._tasks[task_id]

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: Optional[int] = None
    ) -> List[Task]:
        """
        查询任务列表

        Args:
            status: 过滤状态
            limit: 返回数量限制

        Returns:
            任务列表
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status.value]

        if limit:
            tasks = tasks[:limit]

        return tasks

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        priority: Optional[str] = None,
        assigned_employee: Optional[str] = None
    ) -> Task:
        """
        更新任务

        Args:
            task_id: 任务ID
            status: 新状态
            priority: 新优先级
            assigned_employee: 分配员工

        Returns:
            更新后的任务对象
        """
        task = self.get_task(task_id)

        if status:
            task.status = status.value
        if priority:
            task.priority = priority
        if assigned_employee:
            task.assigned_employee = assigned_employee

        self._save_tasks()
        return task

    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> Task:
        """
        取消任务

        Args:
            task_id: 任务ID
            reason: 取消原因

        Returns:
            取消后的任务对象
        """
        task = self.get_task(task_id)
        task.status = TaskStatus.ARCHIVED.value
        task.cancel_reason = reason

        self._save_tasks()
        return task
