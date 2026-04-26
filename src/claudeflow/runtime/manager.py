"""ClaudeFlow 多会话运行时管理。"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from claudeflow.runtime.cli_driver import CliDriver
from claudeflow.runtime.driver_base import (
    DriverRegistry,
    DriverSessionStartResult,
    DriverStatus,
    ExecutorType,
    RuntimeTaskSpec,
)
from claudeflow.runtime.claude_driver import ClaudeDriver
from claudeflow.runtime.codex_driver import CodexDriver


@dataclass
class WorkerTaskSpec:
    """最小可执行任务定义。"""

    task_id: str
    prompt: str
    owner_role: str = "worker-agent"
    task_type: str = "ImplementTask"
    depends_on: List[str] = field(default_factory=list)
    read_paths: List[str] = field(default_factory=list)
    write_paths: List[str] = field(default_factory=list)
    shared_files: List[str] = field(default_factory=list)
    protocol_refs: List[str] = field(default_factory=list)
    design_refs: List[str] = field(default_factory=list)
    priority: str = "medium"


@dataclass
class SessionIndex:
    """任务到宿主会话的索引。

    T105 改造: 增加 executor_type / driver_name 以支持宿主感知回收。
    """

    task_id: str
    session_id: str
    worktree: str
    status: str
    owner_role: str
    task_type: str
    prompt: str
    priority: str
    write_paths: List[str]
    protocol_refs: List[str]
    design_refs: List[str]
    # T105 新增字段
    executor_type: str = ""
    driver_name: str = ""
    phase_id: str = ""
    acceptance_refs: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    # 结果回收字段
    summary: str = ""
    changed_files: List[str] = field(default_factory=list)
    tests: Dict[str, Any] = field(default_factory=dict)
    known_issues: List[str] = field(default_factory=list)
    test_evidence: List[str] = field(default_factory=list)


class RuntimeErrorBase(Exception):
    """运行时基础异常。"""


class WriteLockConflictError(RuntimeErrorBase):
    """写锁冲突。"""


class UnknownTaskError(RuntimeErrorBase):
    """未知任务。"""


class TaskGraphValidationError(RuntimeErrorBase):
    """任务图结构校验失败。"""


class RuntimeReasonCode:
    """运行时原因码常量。"""

    READY = "ready"
    MISSING_DEPENDENCY = "missing_dependency"
    UPSTREAM_FAILED = "upstream_failed"
    WAITING_DEPENDENCY = "waiting_dependency"
    WAITING_SLOT = "waiting_slot"
    WRITE_LOCK_CONFLICT = "write_lock_conflict"
    SESSION_RUNNING = "session_running"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"


@dataclass(frozen=True)
class ReadinessResult:
    """任务就绪性判断结果。"""

    is_runnable: bool
    reason_code: str = RuntimeReasonCode.READY
    reason: str = ""


class RuntimeManager:
    """多会话运行时管理器。

    T105 改造: 支持 driver registry 和宿主感知派发。
    """

    def __init__(
        self,
        repo_path: str,
        driver: Optional[CliDriver] = None,
        runtime_dir_name: str = ".claudeflow",
        worktrees_dir_name: str = ".worktrees",
        branch_prefix: str = "claudeflow",
        # T105 新增: driver registry
        driver_registry: Optional[DriverRegistry] = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.driver = driver or CliDriver()
        self.runtime_dir = self.repo_path / runtime_dir_name
        self.worktrees_dir = self.repo_path / worktrees_dir_name
        self.branch_prefix = branch_prefix

        # T105: 初始化 driver registry
        self.registry = driver_registry or self._create_default_registry()

        self.sessions_dir = self.runtime_dir / "sessions"
        self.checkpoints_dir = self.runtime_dir / "checkpoints"
        self.locks_dir = self.runtime_dir / "locks"
        self.mirror_dir = self.runtime_dir / "transcript-mirror"
        self.handoff_dir = self.runtime_dir / "handoff"
        self.runtime_status_path = self.runtime_dir / "runtime-status.json"
        self.task_graph_path = self.runtime_dir / "task-graph.json"

    def _create_default_registry(self) -> DriverRegistry:
        """创建默认 driver registry，注册 Claude 和 Codex 驱动。"""
        registry = DriverRegistry()
        registry.register(ClaudeDriver(self.driver))
        registry.register(CodexDriver(mock_mode=True))  # 默认 mock 模式
        return registry

    def _convert_worker_to_runtime_spec(
        self,
        worker_spec: WorkerTaskSpec,
        executor_type: str = "claude",
    ) -> RuntimeTaskSpec:
        """T108: 将 WorkerTaskSpec 转换为 RuntimeTaskSpec。

        WorkerTaskSpec 作为兼容适配层，转换后进入宿主感知主链。
        """
        return RuntimeTaskSpec(
            task_id=worker_spec.task_id,
            phase_id="",  # WorkerTaskSpec 无 phase_id
            executor_type=executor_type,
            prompt=worker_spec.prompt,
            read_paths=list(worker_spec.read_paths),
            write_paths=list(worker_spec.write_paths),
            constraints=[],
            acceptance_refs=list(worker_spec.protocol_refs),
            document_refs=list(worker_spec.design_refs),
            priority=worker_spec.priority,
        )

    def _get_task_map(self) -> Dict[str, WorkerTaskSpec]:
        """读取当前 task graph 并按 task_id 建立索引。"""
        graph = self.get_task_graph()
        return {
            task["task_id"]: WorkerTaskSpec(**task)
            for task in graph.get("tasks", [])
        }

    def ensure_layout(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
        for path in (
            self.sessions_dir,
            self.checkpoints_dir,
            self.locks_dir,
            self.mirror_dir,
            self.handoff_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

        if not self.runtime_status_path.exists():
            self._write_json(
                self.runtime_status_path,
                {
                    "repo_path": str(self.repo_path),
                    "active_agents": 0,
                    "queued_tasks": 0,
                    "completed_tasks": 0,
                    "failed_tasks": 0,
                    "intervention_required": False,
                    "running_tasks": [],
                },
            )

    def initialize_task_graph(self, tasks: Sequence[WorkerTaskSpec]) -> None:
        self.ensure_layout()
        self._write_json(
            self.task_graph_path,
            {"tasks": [asdict(task) for task in tasks]},
        )
        status = self._load_runtime_status()
        status["queued_tasks"] = len(tasks)
        self._write_json(self.runtime_status_path, status)

    def load_task_graph(self, task_graph_file: str) -> List[WorkerTaskSpec]:
        """从 JSON 文件加载 task graph。"""
        payload = self._read_json(Path(task_graph_file))
        self.validate_task_graph_payload(payload)
        tasks = []
        for raw in payload.get("tasks", []):
            tasks.append(
                WorkerTaskSpec(
                    task_id=raw["task_id"],
                    prompt=raw["prompt"],
                    owner_role=raw.get("owner_role", "worker-agent"),
                    task_type=raw.get("task_type", "ImplementTask"),
                    depends_on=list(raw.get("depends_on", [])),
                    read_paths=list(raw.get("read_paths", [])),
                    write_paths=list(raw.get("write_paths", [])),
                    shared_files=list(raw.get("shared_files", [])),
                    protocol_refs=list(raw.get("protocol_refs", [])),
                    design_refs=list(raw.get("design_refs", [])),
                    priority=str(raw.get("priority", "medium")),
                )
            )
        return tasks

    def get_task_graph(self) -> Dict[str, Any]:
        """获取当前 runtime task graph。"""
        if not self.task_graph_path.exists():
            return {"tasks": []}
        return self._read_json(self.task_graph_path)

    def validate_task_graph_payload(self, payload: Dict[str, Any]) -> None:
        """对 task graph 做最小结构校验。"""
        if not isinstance(payload, dict):
            raise TaskGraphValidationError("task graph 顶层必须是对象")

        tasks = payload.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            raise TaskGraphValidationError("task graph 必须包含非空 tasks 数组")

        seen_ids = set()
        for idx, raw in enumerate(tasks):
            if not isinstance(raw, dict):
                raise TaskGraphValidationError(f"tasks[{idx}] 必须是对象")
            task_id = raw.get("task_id")
            prompt = raw.get("prompt")
            if not task_id or not isinstance(task_id, str):
                raise TaskGraphValidationError(f"tasks[{idx}].task_id 缺失或非法")
            if task_id in seen_ids:
                raise TaskGraphValidationError(f"task_id 重复: {task_id}")
            seen_ids.add(task_id)
            if not prompt or not isinstance(prompt, str):
                raise TaskGraphValidationError(f"tasks[{idx}].prompt 缺失或非法")

            for field_name in (
                "depends_on",
                "read_paths",
                "write_paths",
                "shared_files",
                "protocol_refs",
                "design_refs",
            ):
                if field_name in raw and not isinstance(raw[field_name], list):
                    raise TaskGraphValidationError(f"tasks[{idx}].{field_name} 必须是数组")
            if "priority" in raw and not isinstance(raw["priority"], (str, int)):
                raise TaskGraphValidationError(f"tasks[{idx}].priority 必须是字符串或整数")

    def get_dispatch_plan(self, executor_type: str = "claude") -> Dict[str, Any]:
        """T109: 计算调度计划，包含 RunnableTaskSpec 与 blocked 任务。

        RuntimeTaskSpec 是主链任务模型。默认 executor_type 为 claude。
        旧 WorkerTaskSpec 版本保留为 get_dispatch_plan_compat()。
        """
        tasks = list(self._get_task_map().values())
        sessions = {item["task_id"]: item for item in self.list_session_indexes()}
        task_ids = {task.task_id for task in tasks}

        runnable: List[RuntimeTaskSpec] = []
        blocked: List[Dict[str, Any]] = []
        for task in tasks:
            if task.task_id in sessions:
                continue
            readiness = self._get_task_readiness(task, sessions, task_ids)
            if readiness.is_runnable:
                # T109: 转换为 RuntimeTaskSpec（主模型）
                spec = self._convert_worker_to_runtime_spec(task, executor_type=executor_type)
                runnable.append(spec)
            else:
                blocked.append(
                    {
                        "task_id": task.task_id,
                        "priority": task.priority,
                        "reason_code": readiness.reason_code,
                        "reason": readiness.reason,
                    }
                )
        runnable.sort(key=lambda spec: self._task_sort_key_from_priority(spec.priority))
        blocked.sort(key=lambda item: self._task_sort_key_from_priority(item["priority"]))
        return {
            "runnable": runnable,
            "blocked": blocked,
            "running": self._build_running_items(sessions, task_ids),
        }

    def get_dispatch_plan_compat(self) -> Dict[str, Any]:
        """T109 兼容: WorkerTaskSpec 版本的调度计划。

        已弃用，建议使用 get_dispatch_plan() 返回 RuntimeTaskSpec 主模型。
        """
        tasks = list(self._get_task_map().values())
        sessions = {item["task_id"]: item for item in self.list_session_indexes()}
        task_ids = {task.task_id for task in tasks}

        runnable: List[WorkerTaskSpec] = []
        blocked: List[Dict[str, Any]] = []
        for task in tasks:
            if task.task_id in sessions:
                continue
            readiness = self._get_task_readiness(task, sessions, task_ids)
            if readiness.is_runnable:
                runnable.append(task)
            else:
                blocked.append(
                    {
                        "task_id": task.task_id,
                        "priority": task.priority,
                        "reason_code": readiness.reason_code,
                        "reason": readiness.reason,
                    }
                )
        runnable.sort(key=self._task_sort_key)
        blocked.sort(key=lambda item: self._task_sort_key_from_priority(item["priority"]))
        return {
            "runnable": runnable,
            "blocked": blocked,
            "running": self._build_running_items(sessions, task_ids),
        }

    def explain_task(self, task_id: str) -> Dict[str, Any]:
        """T108: 解释单个任务当前为何可运行、阻塞或已结束。

        输出包含宿主信息（executor_type / driver_name）。
        """
        task_map = self._get_task_map()
        task = task_map.get(task_id)
        if task is None:
            raise UnknownTaskError(f"task graph 中不存在任务: {task_id}")

        sessions = {item["task_id"]: item for item in self.list_session_indexes()}
        session = sessions.get(task_id)
        if session:
            # T108: 输出宿主字段
            return {
                "task_id": task_id,
                "state": session["status"],
                "priority": task.priority,
                "reason_code": self._session_reason_code(session["status"]),
                "reason": f"任务已有会话记录，当前状态: {session['status']}",
                "dependencies": list(task.depends_on),
                "executor_type": session.get("executor_type", ""),
                "driver_name": session.get("driver_name", ""),
            }

        readiness = self._get_task_readiness(task, sessions, set(task_map.keys()))
        return {
            "task_id": task_id,
            "state": "runnable" if readiness.is_runnable else "blocked",
            "priority": task.priority,
            "reason_code": readiness.reason_code,
            "reason": readiness.reason or "依赖已满足，可进入调度队列",
            "dependencies": list(task.depends_on),
            "executor_type": "",  # 未派发时为空
            "driver_name": "",    # 未派发时为空
        }

    def get_runnable_tasks(self) -> List[WorkerTaskSpec]:
        """T109 兼容: 基于 WorkerTaskSpec 的可运行任务列表。

        已弃用，建议使用 get_runnable_specs() 返回 RuntimeTaskSpec 主模型。
        """
        plan = self.get_dispatch_plan_compat()
        return list(plan["runnable"])

    def get_runnable_specs(self, executor_type: str = "claude") -> List[RuntimeTaskSpec]:
        """T109: 返回可运行的 RuntimeTaskSpec 列表。

        RuntimeTaskSpec 是主链任务模型。
        """
        plan = self.get_dispatch_plan(executor_type=executor_type)
        return list(plan["runnable"])

    def get_dispatch_plan_specs(self, executor_type: str = "claude") -> Dict[str, Any]:
        """T109: 调度计划的别名（已合并到 get_dispatch_plan）。

        保留此方法向后兼容，建议直接使用 get_dispatch_plan()。
        """
        return self.get_dispatch_plan(executor_type=executor_type)

    def _get_task_readiness(
        self,
        task: WorkerTaskSpec,
        sessions: Dict[str, Dict[str, Any]],
        task_ids: set[str],
    ) -> ReadinessResult:
        missing_dependencies = [dep for dep in task.depends_on if dep not in task_ids]
        if missing_dependencies:
            return ReadinessResult(
                is_runnable=False,
                reason_code=RuntimeReasonCode.MISSING_DEPENDENCY,
                reason=f"依赖任务不存在: {', '.join(missing_dependencies)}",
            )

        failed_dependencies = [
            dep for dep in task.depends_on
            if sessions.get(dep, {}).get("status") == "failed"
        ]
        if failed_dependencies:
            return ReadinessResult(
                is_runnable=False,
                reason_code=RuntimeReasonCode.UPSTREAM_FAILED,
                reason=f"上游失败，按策略跳过: {', '.join(failed_dependencies)}",
            )

        waiting_dependencies = []
        for dep in task.depends_on:
            dep_status = sessions.get(dep, {}).get("status")
            if dep_status != "completed":
                waiting_dependencies.append(f"{dep}({dep_status or 'pending'})")

        if waiting_dependencies:
            return ReadinessResult(
                is_runnable=False,
                reason_code=RuntimeReasonCode.WAITING_DEPENDENCY,
                reason=f"等待依赖完成: {', '.join(waiting_dependencies)}",
            )

        return ReadinessResult(is_runnable=True)

    @staticmethod
    def _build_running_items(
        sessions: Dict[str, Dict[str, Any]],
        task_ids: set[str],
    ) -> List[Dict[str, Any]]:
        running = []
        for task_id, session in sessions.items():
            if task_id not in task_ids:
                continue
            if session.get("status") != "running":
                continue
            running.append(
                {
                    "task_id": task_id,
                    "priority": session.get("priority", "medium"),
                    "reason_code": RuntimeReasonCode.SESSION_RUNNING,
                    "reason": "任务已有运行中的会话",
                }
            )
        running.sort(key=lambda item: (RuntimeManager._task_priority_value(item["priority"]), item["task_id"]))
        return running

    @staticmethod
    def _session_reason_code(status: str) -> str:
        mapping = {
            "running": RuntimeReasonCode.SESSION_RUNNING,
            "completed": RuntimeReasonCode.SESSION_COMPLETED,
            "failed": RuntimeReasonCode.SESSION_FAILED,
        }
        return mapping.get(status, f"session_{status}")

    @staticmethod
    def _task_priority_value(priority: str) -> int:
        mapping = {
            "p0": 0,
            "urgent": 0,
            "critical": 0,
            "high": 1,
            "medium": 2,
            "normal": 2,
            "low": 3,
            "p1": 1,
            "p2": 2,
            "p3": 3,
            "最高": 0,
            "高": 1,
            "中": 2,
            "低": 3,
        }
        normalized = str(priority).strip().lower()
        if normalized.isdigit():
            return int(normalized)
        return mapping.get(normalized, 2)

    @classmethod
    def _task_sort_key(cls, task: WorkerTaskSpec) -> Tuple[int, str]:
        return (cls._task_priority_value(task.priority), task.task_id)

    @classmethod
    def _task_sort_key_from_priority(cls, priority: str) -> Tuple[int, str]:
        return (cls._task_priority_value(priority), str(priority))

    def dispatch_runnable_tasks(
        self,
        base_branch: str = "HEAD",
        limit: Optional[int] = None,
        max_concurrent: Optional[int] = None,
        executor_type: str = "claude",
    ) -> Dict[str, Any]:
        """T109: 启动所有当前可运行任务。

        使用 RuntimeTaskSpec 作为主链模型，WorkerTaskSpec 通过兼容层转换。
        默认 executor_type 为 claude，可通过参数指定。
        """
        plan = self.get_dispatch_plan(executor_type=executor_type)
        runnable_specs = list(plan["runnable"])
        blocked = list(plan["blocked"])
        started: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        status = self.get_runtime_status()
        active_agents = int(status.get("active_agents", 0))

        available_slots = len(runnable_specs)
        if max_concurrent is not None:
            available_slots = max(max_concurrent - active_agents, 0)
        if limit is not None:
            available_slots = min(available_slots, limit)

        deferred = runnable_specs[available_slots:]
        for spec in deferred:
            blocked.append(
                {
                    "task_id": spec.task_id,
                    "priority": spec.priority,
                    "reason_code": RuntimeReasonCode.WAITING_SLOT,
                    "reason": "等待可用并发槽位",
                }
            )

        for spec in runnable_specs[:available_slots]:
            try:
                # T109: RuntimeTaskSpec 主链直接派发
                index, reason_code, reason = self.start_worker_with_spec(spec, base_branch)
                if index:
                    started.append(asdict(index))
                else:
                    skipped.append(
                        {
                            "task_id": spec.task_id,
                            "reason_code": reason_code,
                            "reason": reason,
                        }
                    )
            except WriteLockConflictError as exc:
                skipped.append(
                    {
                        "task_id": spec.task_id,
                        "reason_code": RuntimeReasonCode.WRITE_LOCK_CONFLICT,
                        "reason": str(exc),
                    }
                )

        return {
            "started": started,
            "skipped": skipped,
            "blocked": blocked,
            "runnable_count": len(runnable_specs),
            "blocked_count": len(blocked),
            "available_slots": available_slots,
            "active_agents": active_agents,
            "max_concurrent": max_concurrent,
        }

    def start_worker(
        self,
        task: WorkerTaskSpec,
        base_branch: str = "HEAD",
        executor_type: str = "claude",
    ) -> SessionIndex:
        """T108: 启动 worker 任务，通过 registry 派发。

        WorkerTaskSpec 作为兼容输入，转换为 RuntimeTaskSpec 后进入宿主感知主链。
        默认 executor_type 为 claude，但可通过参数指定宿主。

        Args:
            task: WorkerTaskSpec 兼容输入
            base_branch: 基础分支
            executor_type: 执行器类型（claude/codex）

        Returns:
            SessionIndex

        Raises:
            WriteLockConflictError: 写锁冲突
            RuntimeErrorBase: 驱动派发失败
        """
        self.ensure_layout()
        self.acquire_write_lock(task)

        try:
            # T108: 转换为 RuntimeTaskSpec 并通过 registry 派发
            spec = self._convert_worker_to_runtime_spec(task, executor_type=executor_type)
            index, reason_code, reason = self.start_worker_with_spec(spec, base_branch=base_branch)

            if index is None:
                raise RuntimeErrorBase(f"派发失败: {reason_code} - {reason}")

            return index
        except Exception:
            # Blocker fix: 失败时释放写锁
            self.release_write_lock(task.task_id)
            raise

    def start_worker_with_spec(
        self,
        spec: RuntimeTaskSpec,
        base_branch: str = "HEAD",
    ) -> tuple[Optional[SessionIndex], str, str]:
        """使用 RuntimeTaskSpec 派发任务（T105 新增）。

        根据 executor_type 从 registry 选择驱动并派发。

        Args:
            spec: 运行时任务规格
            base_branch: 基础分支

        Returns:
            (SessionIndex 或 None, reason_code, reason)
        """
        self.ensure_layout()

        # 验证 executor_type
        is_valid, reason_code = self.registry.validate_executor_type(spec.executor_type)
        if not is_valid:
            return None, reason_code, f"executor_type={spec.executor_type} 不支持"

        driver = self.registry.get_driver(spec.executor_type)
        if driver is None:
            return None, "driver_not_registered", f"{spec.executor_type} 驱动未注册"

        # 创建 worktree
        worktree_path = self.create_worktree(spec.task_id, base_branch=base_branch)

        # 调用驱动启动任务
        result = driver.start_task(spec, cwd=str(worktree_path))

        if not result.success:
            return None, result.reason_code, result.reason

        # 构建并写入 SessionIndex
        # T108/T109 兼容: protocol_refs 从 acceptance_refs 复制（WorkerTaskSpec 协议引用迁移）
        index = SessionIndex(
            task_id=spec.task_id,
            session_id=result.session_id,
            worktree=str(worktree_path),
            status="running",
            owner_role="worker-agent",
            task_type="GovernanceTask",
            prompt=spec.prompt,
            priority=spec.priority,
            write_paths=list(spec.write_paths),
            protocol_refs=list(spec.acceptance_refs),  # T109 兼容: 从 acceptance_refs 复制
            design_refs=list(spec.document_refs),
            executor_type=spec.executor_type,
            driver_name=result.driver_name,
            phase_id=spec.phase_id,
            acceptance_refs=list(spec.acceptance_refs),
            constraints=list(spec.constraints),
        )

        self._write_json(self._session_path(spec.task_id), asdict(index))
        self._refresh_runtime_status()

        return index, "", ""

    def dispatch_from_governance(
        self,
        governance_root: str,
        phase_id: str,
        base_branch: str = "HEAD",
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """从治理任务包目录派发任务（T105 新增）。

        Args:
            governance_root: .super-dev 根目录
            phase_id: 阶段 ID
            base_branch: 基础分支
            limit: 最大派发数量

        Returns:
            派发结果汇总
        """
        from claudeflow.runtime.governance_adapter import GovernanceRuntimeAdapter

        adapter = GovernanceRuntimeAdapter()
        specs, errors = adapter.load_phase_tasks(governance_root, phase_id)

        if errors:
            # T106: 统一返回契约
            status = self.get_runtime_status()
            active_agents = int(status.get("active_agents", 0))

            return {
                "started": [],
                "skipped": [
                    {
                        "reason_code": "task_package_load_error",
                        "reason": e.reason,
                        "file_path": e.file_path,
                    }
                    for e in errors
                ],
                "blocked": [],
                "runnable_count": 0,
                "blocked_count": 0,
                "available_slots": 999,  # 无硬限制时返回足够大值
                "active_agents": active_agents,
                "max_concurrent": None,  # 治理场景无硬限制
            }

        # 按优先级排序
        specs = sorted(specs, key=lambda s: self._task_priority_value(s.priority))

        if limit is not None:
            specs = specs[:limit]

        started: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []

        for spec in specs:
            index, reason_code, reason = self.start_worker_with_spec(spec, base_branch)
            if index:
                started.append(asdict(index))
            else:
                skipped.append({
                    "task_id": spec.task_id,
                    "executor_type": spec.executor_type,
                    "reason_code": reason_code,
                    "reason": reason,
                })

        # T106: 统一返回契约，与 dispatch_runnable_tasks 相同
        status = self.get_runtime_status()
        active_agents = int(status.get("active_agents", 0))

        return {
            "started": started,
            "skipped": skipped,
            "blocked": [],
            "runnable_count": len(specs),
            "blocked_count": 0,
            "available_slots": 999,  # 无硬限制时返回足够大值
            "active_agents": active_agents,
            "max_concurrent": None,  # 治理场景无硬限制
        }

    def collect_session_result(
        self,
        task_id: str,
    ) -> Dict[str, Any]:
        """收集任务会话执行结果（T105 新增）。

        从对应 driver 收集结构化结果:
        - summary
        - changed_files
        - tests
        - known_issues
        - test_evidence

        Args:
            task_id: 任务 ID

        Returns:
            结果字典
        """
        index = self.get_session_index(task_id)
        executor_type = index.get("executor_type", "claude")
        session_id = index.get("session_id", "")

        driver = self.registry.get_driver(executor_type)
        if driver is None:
            return {
                "task_id": task_id,
                "success": False,
                "reason_code": "driver_not_registered",
                "reason": f"{executor_type} 驱动未注册",
            }

        result = driver.collect_result(session_id)

        # 更新 SessionIndex
        index["summary"] = result.summary
        index["changed_files"] = result.changed_files
        index["tests"] = result.tests
        index["known_issues"] = result.known_issues
        index["test_evidence"] = result.test_evidence
        index["status"] = "completed" if result.success else "failed"

        self._write_json(self._session_path(task_id), index)
        self._refresh_runtime_status()

        return {
            "task_id": task_id,
            "success": result.success,
            "executor_type": result.executor_type,
            "driver_name": result.driver_name,
            "summary": result.summary,
            "changed_files": result.changed_files,
            "tests": result.tests,
            "known_issues": result.known_issues,
            "test_evidence": result.test_evidence,
        }

    def get_supported_executors(self) -> List[str]:
        """获取已注册且可派发的 executor_type 列表。"""
        return self.registry.get_supported_types()

    def checkpoint_task(
        self,
        task_id: str,
        summary: str,
        changed_files: Optional[List[str]] = None,
        tests: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        index = self.get_session_index(task_id)
        checkpoint = {
            "task_id": task_id,
            "session_id": index["session_id"],
            "summary": summary,
            "changed_files": changed_files or [],
            "tests": tests or {},
            "protocol_refs": index.get("protocol_refs", []),
            "design_refs": index.get("design_refs", []),
        }
        self._write_json(self.checkpoints_dir / f"{task_id}.json", checkpoint)

        index["summary"] = summary
        index["changed_files"] = changed_files or []
        index["tests"] = tests or {}
        self._write_json(self._session_path(task_id), index)
        return checkpoint

    def _update_task_status(self, task_id: str, status: str, summary: str = "") -> Dict[str, Any]:
        """更新任务状态并刷新 runtime 统计。"""
        index = self.get_session_index(task_id)
        index["status"] = status
        if summary:
            index["summary"] = summary
        self._write_json(self._session_path(task_id), index)
        self.release_write_lock(task_id)
        self._refresh_runtime_status()
        return index

    def complete_worker(
        self,
        task_id: str,
        summary: str = "",
        changed_files: Optional[List[str]] = None,
        tests: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if summary or changed_files or tests:
            self.checkpoint_task(task_id, summary, changed_files, tests)
        return self._update_task_status(task_id, "completed")

    def fail_worker(self, task_id: str, reason: str) -> Dict[str, Any]:
        index = self.get_session_index(task_id)
        self.checkpoint_task(
            task_id,
            reason,
            changed_files=index.get("changed_files", []),
            tests=index.get("tests", {}),
        )
        return self._update_task_status(task_id, "failed", summary=reason)

    def create_worktree(self, task_id: str, base_branch: str = "HEAD") -> Path:
        self.ensure_layout()
        worktree_path = self.worktrees_dir / task_id
        if worktree_path.exists():
            return worktree_path

        branch_name = f"{self.branch_prefix}/{task_id}"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo_path),
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree_path),
                base_branch,
            ],
            check=True,
        )
        return worktree_path

    def acquire_write_lock(self, task: WorkerTaskSpec) -> Dict[str, Any]:
        requested = set(task.write_paths)
        if not requested:
            lock = {"task_id": task.task_id, "paths": [], "scope": "read_only"}
            self._write_json(self._lock_path(task.task_id), lock)
            return lock

        for lock_path in self.locks_dir.glob("*.json"):
            existing = self._read_json(lock_path)
            existing_paths = set(existing.get("paths", []))
            if requested & existing_paths:
                raise WriteLockConflictError(
                    f"任务 {task.task_id} 与 {existing['task_id']} 写入路径冲突: "
                    f"{sorted(requested & existing_paths)}"
                )

        lock = {
            "task_id": task.task_id,
            "paths": sorted(requested),
            "scope": "write_paths",
        }
        self._write_json(self._lock_path(task.task_id), lock)
        return lock

    def release_write_lock(self, task_id: str) -> None:
        lock_path = self._lock_path(task_id)
        if lock_path.exists():
            lock_path.unlink()

    def get_session_index(self, task_id: str) -> Dict[str, Any]:
        path = self._session_path(task_id)
        if not path.exists():
            raise UnknownTaskError(f"未找到任务会话索引: {task_id}")
        return self._read_json(path)

    def get_runtime_status(self) -> Dict[str, Any]:
        """获取运行时总览状态。"""
        return self._load_runtime_status()

    def list_session_indexes(self) -> List[Dict[str, Any]]:
        """列出当前所有任务会话索引。"""
        self.ensure_layout()
        return [self._read_json(path) for path in sorted(self.sessions_dir.glob("*.json"))]

    def _refresh_runtime_status(self) -> None:
        self.ensure_layout()
        sessions = [self._read_json(path) for path in self.sessions_dir.glob("*.json")]
        status = self._load_runtime_status()
        status["active_agents"] = sum(1 for item in sessions if item["status"] == "running")
        status["completed_tasks"] = sum(1 for item in sessions if item["status"] == "completed")
        status["failed_tasks"] = sum(1 for item in sessions if item["status"] == "failed")
        status["intervention_required"] = status["failed_tasks"] > 0
        status["running_tasks"] = [item["task_id"] for item in sessions if item["status"] == "running"]
        status["queued_tasks"] = self._queued_tasks_count(sessions)
        self._write_json(self.runtime_status_path, status)

    def _queued_tasks_count(self, sessions: Sequence[Dict[str, Any]]) -> int:
        if not self.task_graph_path.exists():
            return 0
        task_graph = self._read_json(self.task_graph_path)
        all_ids = {task["task_id"] for task in task_graph.get("tasks", [])}
        session_ids = {item["task_id"] for item in sessions}
        return len(all_ids - session_ids)

    def _load_runtime_status(self) -> Dict[str, Any]:
        self.ensure_layout()
        return self._read_json(self.runtime_status_path)

    def _session_path(self, task_id: str) -> Path:
        return self.sessions_dir / f"{task_id}.json"

    def _lock_path(self, task_id: str) -> Path:
        return self.locks_dir / f"{task_id}.json"

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
