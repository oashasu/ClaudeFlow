"""RuntimeDriver 抽象接口与统一返回对象。

T101 实现:
- 定义 RuntimeDriver 协议接口
- 统一 DriverSessionStartResult / DriverExecutionResult 返回结构
- 支持 claude / codex 双宿主抽象
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutorType(Enum):
    """支持的宿主类型枚举。"""

    CLAUDE = "claude"
    CODEX = "codex"
    # 保留但本阶段不允许真实派发
    FUTURE = "future"


class DriverStatus(Enum):
    """驱动会话状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DriverSessionStartResult:
    """驱动启动会话的统一返回结构。"""

    success: bool
    session_id: str = ""
    driver_name: str = ""
    executor_type: str = ""
    worktree: str = ""
    reason_code: str = ""
    reason: str = ""
    process_info: Optional[Dict[str, Any]] = None


@dataclass
class DriverSessionState:
    """驱动会话状态快照。"""

    session_id: str
    task_id: str
    executor_type: str
    driver_name: str
    worktree: str
    status: DriverStatus
    prompt: str
    started_at: str = ""
    events_count: int = 0
    last_event_type: str = ""


@dataclass
class DriverExecutionResult:
    """驱动执行结果的统一返回结构。"""

    success: bool
    session_id: str
    task_id: str
    executor_type: str
    driver_name: str
    summary: str = ""
    changed_files: List[str] = field(default_factory=list)
    tests: Dict[str, Any] = field(default_factory=dict)
    known_issues: List[str] = field(default_factory=list)
    test_evidence: List[str] = field(default_factory=list)
    reason_code: str = ""
    reason: str = ""
    raw_events: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RuntimeTaskSpec:
    """治理任务包到 runtime 的映射对象。

    来源: TaskPackage YAML
    映射规则:
    - id -> task_id
    - phase_id -> phase_id
    - executor_type -> executor_type
    - inputs -> read_paths/document_refs
    - allowed_write_paths -> write_paths
    - constraints -> constraints
    - acceptance_refs -> acceptance_refs
    """

    task_id: str
    phase_id: str
    executor_type: str
    prompt: str = ""
    read_paths: List[str] = field(default_factory=list)
    write_paths: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    acceptance_refs: List[str] = field(default_factory=list)
    document_refs: List[str] = field(default_factory=list)
    priority: str = "medium"


class RuntimeDriver(ABC):
    """RuntimeDriver 抽象接口。

    统一不同宿主的启动、监控、干预、取消、结果回收接口。
    所有具体驱动（ClaudeDriver / CodexDriver）必须实现此接口。
    """

    @property
    @abstractmethod
    def driver_name(self) -> str:
        """驱动名称标识。"""
        pass

    @property
    @abstractmethod
    def executor_type(self) -> ExecutorType:
        """宿主类型。"""
        pass

    @abstractmethod
    def start_task(
        self,
        task_spec: RuntimeTaskSpec,
        cwd: Optional[str] = None,
    ) -> DriverSessionStartResult:
        """启动任务执行。

        Args:
            task_spec: 运行时任务规格
            cwd: 工作目录（可选）

        Returns:
            DriverSessionStartResult: 启动结果
        """
        pass

    @abstractmethod
    def intervene(self, session_id: str, prompt: str) -> bool:
        """干预正在执行的会话。

        Args:
            session_id: 会话 ID
            prompt: 干预内容

        Returns:
            是否成功注入干预
        """
        pass

    @abstractmethod
    def cancel(self, session_id: str) -> bool:
        """取消会话执行。

        Args:
            session_id: 会话 ID

        Returns:
            是否成功取消
        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[DriverSessionState]:
        """获取会话状态快照。

        Args:
            session_id: 会话 ID

        Returns:
            会话状态或 None
        """
        pass

    @abstractmethod
    def get_status(self, session_id: str) -> DriverStatus:
        """获取会话状态枚举。

        Args:
            session_id: 会话 ID

        Returns:
            DriverStatus
        """
        pass

    @abstractmethod
    def collect_events(self, session_id: str) -> List[Dict[str, Any]]:
        """收集会话事件列表。

        Args:
            session_id: 会话 ID

        Returns:
            事件字典列表
        """
        pass

    @abstractmethod
    def collect_result(self, session_id: str) -> DriverExecutionResult:
        """收集执行结果。

        Args:
            session_id: 会话 ID

        Returns:
            DriverExecutionResult
        """
        pass


class DriverRegistry:
    """驱动注册表。

    职责:
    - 根据 executor_type 返回对应驱动
    - 对不支持值给出结构化错误
    """

    def __init__(self) -> None:
        self._drivers: Dict[ExecutorType, RuntimeDriver] = {}

    def register(self, driver: RuntimeDriver) -> None:
        """注册驱动实例。"""
        self._drivers[driver.executor_type] = driver

    def get_driver(self, executor_type: str) -> Optional[RuntimeDriver]:
        """根据 executor_type 获取驱动。"""
        try:
            et = ExecutorType(executor_type)
            return self._drivers.get(et)
        except ValueError:
            return None

    def is_supported(self, executor_type: str) -> bool:
        """检查 executor_type 是否支持。"""
        try:
            et = ExecutorType(executor_type)
            return et in self._drivers and et != ExecutorType.FUTURE
        except ValueError:
            return False

    def get_supported_types(self) -> List[str]:
        """获取已注册且可派发的宿主类型列表。"""
        return [
            et.value for et in self._drivers.keys()
            if et != ExecutorType.FUTURE
        ]

    def validate_executor_type(self, executor_type: str) -> tuple[bool, str]:
        """校验 executor_type 并返回结构化结果。

        Returns:
            (is_valid, reason_code)
        """
        try:
            et = ExecutorType(executor_type)
        except ValueError:
            return False, "unsupported_executor_type"

        if et == ExecutorType.FUTURE:
            return False, "future_executor_not_dispatchable"

        if et not in self._drivers:
            return False, "driver_not_registered"

        return True, ""