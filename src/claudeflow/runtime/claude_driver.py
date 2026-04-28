"""ClaudeDriver — Claude CLI 宿主的 RuntimeDriver 实现。

T102 实现:
- 封装现有 CliDriver
- 实现 RuntimeDriver 接口
- 保持现有 Claude 路径兼容
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claudeflow.runtime.cli_driver import CliDriver, CliSession
from claudeflow.runtime.driver_base import (
    DriverExecutionResult,
    DriverSessionStartResult,
    DriverSessionState,
    DriverStatus,
    ExecutorType,
    RuntimeDriver,
    RuntimeTaskSpec,
)


class ClaudeDriver(RuntimeDriver):
    """Claude CLI 驱动实现。

    封装现有 CliDriver，实现 RuntimeDriver 协议。
    保持现有 Claude 路径完全兼容。
    """

    def __init__(self, cli_driver: Optional[CliDriver] = None) -> None:
        """初始化 ClaudeDriver。

        Args:
            cli_driver: 可选的现有 CliDriver 实例，默认创建新实例
        """
        self._cli = cli_driver or CliDriver()
        self._session_states: Dict[str, DriverSessionState] = {}
        self._session_tasks: Dict[str, str] = {}  # session_id -> task_id
        self._lock = threading.Lock()

    @property
    def driver_name(self) -> str:
        return "claude-driver"

    @property
    def executor_type(self) -> ExecutorType:
        return ExecutorType.CLAUDE

    def start_task(
        self,
        task_spec: RuntimeTaskSpec,
        cwd: Optional[str] = None,
    ) -> DriverSessionStartResult:
        """启动 Claude CLI 执行任务。

        Args:
            task_spec: 运行时任务规格
            cwd: 工作目录

        Returns:
            DriverSessionStartResult
        """
        try:
            process, session_id = self._cli.start_session(
                prompt=task_spec.prompt,
                cwd=cwd,
            )
            worktree = cwd or ""

            state = DriverSessionState(
                session_id=session_id,
                task_id=task_spec.task_id,
                executor_type=self.executor_type.value,
                driver_name=self.driver_name,
                worktree=worktree,
                status=DriverStatus.RUNNING,
                prompt=task_spec.prompt,
                started_at=datetime.now(timezone.utc).isoformat(),
            )

            with self._lock:
                self._session_states[session_id] = state
                self._session_tasks[session_id] = task_spec.task_id

            return DriverSessionStartResult(
                success=True,
                session_id=session_id,
                driver_name=self.driver_name,
                executor_type=self.executor_type.value,
                worktree=worktree,
                process_info={"pid": process.pid},
            )

        except Exception as exc:
            return DriverSessionStartResult(
                success=False,
                reason_code="driver_start_failed",
                reason=str(exc),
                driver_name=self.driver_name,
                executor_type=self.executor_type.value,
            )

    def intervene(self, session_id: str, prompt: str) -> bool:
        """干预 Claude 会话。"""
        try:
            self._cli.intervene(session_id, prompt)
            return True
        except Exception:
            return False

    def cancel(self, session_id: str) -> bool:
        """取消 Claude 会话。"""
        try:
            self._cli.clear_session(session_id)
            with self._lock:
                if session_id in self._session_states:
                    self._session_states[session_id].status = DriverStatus.CANCELLED
            return True
        except Exception:
            return False

    def get_session(self, session_id: str) -> Optional[DriverSessionState]:
        """获取会话状态。"""
        with self._lock:
            state = self._session_states.get(session_id)
            if state is None:
                return None

            cli_session = self._cli.get_session(session_id)
            if cli_session:
                state.events_count = len(cli_session.events)
                if cli_session.events:
                    last_event = cli_session.events[-1]
                    state.last_event_type = last_event.get("type", "")

            return state

    def get_status(self, session_id: str) -> DriverStatus:
        """获取会话状态枚举。"""
        state = self.get_session(session_id)
        return state.status if state else DriverStatus.PENDING

    def collect_events(self, session_id: str) -> List[Dict[str, Any]]:
        """收集会话事件。"""
        cli_session = self._cli.get_session(session_id)
        if cli_session:
            return list(cli_session.events)
        return []

    def collect_result(self, session_id: str) -> DriverExecutionResult:
        """收集执行结果。

        从 CLI 事件流中提取:
        - summary: result 事件文本
        - changed_files: 从 tool_use 事件解析
        - tests: 从 tool_use 事件解析
        """
        cli_session = self._cli.get_session(session_id)
        task_id = self._session_tasks.get(session_id, "")

        if not cli_session:
            return DriverExecutionResult(
                success=False,
                session_id=session_id,
                task_id=task_id,
                executor_type=self.executor_type.value,
                driver_name=self.driver_name,
                reason_code="session_not_found",
                reason=f"会话不存在: {session_id}",
            )

        is_complete, summary = self._cli.detect_completion(cli_session.events)

        changed_files: List[str] = []
        tests: Dict[str, Any] = {}
        known_issues: List[str] = []
        test_evidence: List[str] = []

        for event in cli_session.events:
            parsed = self._cli.parse_assistant_event(event)
            if parsed and parsed["type"] == "tool_use":
                tool_name = parsed["tool_name"]
                tool_input = parsed["tool_input"] or {}

                if tool_name in ("Edit", "Write"):
                    file_path = tool_input.get("file_path", "")
                    if file_path:
                        changed_files.append(file_path)

                if tool_name == "Bash":
                    cmd = tool_input.get("command", "")
                    if "test" in cmd.lower() or "pytest" in cmd.lower():
                        test_evidence.append(cmd)
                    if "error" in cmd.lower() or "fail" in cmd.lower():
                        known_issues.append(cmd)

        with self._lock:
            if session_id in self._session_states:
                self._session_states[session_id].status = (
                    DriverStatus.COMPLETED if is_complete else DriverStatus.RUNNING
                )

        return DriverExecutionResult(
            success=is_complete,
            session_id=session_id,
            task_id=task_id,
            executor_type=self.executor_type.value,
            driver_name=self.driver_name,
            summary=summary,
            changed_files=changed_files,
            tests=tests,
            known_issues=known_issues,
            test_evidence=test_evidence,
            raw_events=cli_session.events,
        )

    def get_cli_driver(self) -> CliDriver:
        """获取底层 CliDriver 实例（向后兼容）。"""
        return self._cli