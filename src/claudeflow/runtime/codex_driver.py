"""CodexDriver — Codex CLI 宿主的 RuntimeDriver 实现。

T103 实现:
- 提供 codex 宿主的最小执行/可测试入口
- 将宿主细节限制在 driver 内部
- 不支持真实执行时可用 mock 覆盖测试路径
"""

from __future__ import annotations

import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claudeflow.runtime.driver_base import (
    DriverExecutionResult,
    DriverSessionStartResult,
    DriverSessionState,
    DriverStatus,
    ExecutorType,
    RuntimeDriver,
    RuntimeTaskSpec,
)


class CodexSession:
    """Codex 会话信息（内部结构）。"""

    def __init__(
        self,
        session_id: str,
        process: Optional[subprocess.Popen] = None,
        prompt: str = "",
        cwd: Optional[str] = None,
    ) -> None:
        self.session_id = session_id
        self.process = process
        self.prompt = prompt
        self.cwd = cwd or ""
        self.events: List[Dict[str, Any]] = []
        self.started_at = datetime.now(timezone.utc).isoformat()


class CodexDriver(RuntimeDriver):
    """Codex CLI 驱动实现。

    提供 codex 宿主的最小执行入口。
    将宿主细节（命令构造、事件解析）封装在 driver 内部。
    """

    CODEX_CMD = "codex"

    def __init__(self, mock_mode: bool = False) -> None:
        """初始化 CodexDriver。

        Args:
            mock_mode: True 时不执行真实 CLI，用于测试覆盖
        """
        self._mock_mode = mock_mode
        self._sessions: Dict[str, CodexSession] = {}
        self._session_tasks: Dict[str, str] = {}
        self._lock = threading.Lock()

    @property
    def driver_name(self) -> str:
        return "codex-driver"

    @property
    def executor_type(self) -> ExecutorType:
        return ExecutorType.CODEX

    def _build_start_command(
        self,
        prompt: str,
        session_id: str,
    ) -> List[str]:
        """构造 Codex 启动命令（宿主细节封装）。"""
        return [
            self.CODEX_CMD,
            "-p",
            prompt,
            "--session-id",
            session_id,
            "--output-format",
            "stream-json",
            "--verbose",
        ]

    def _build_intervene_command(
        self,
        session_id: str,
        prompt: str,
    ) -> List[str]:
        """构造 Codex 干预命令（宿主细节封装）。"""
        return [
            self.CODEX_CMD,
            "-p",
            "--resume",
            session_id,
            prompt,
            "--output-format",
            "stream-json",
        ]

    def _mock_start_session(
        self,
        task_spec: RuntimeTaskSpec,
        cwd: Optional[str] = None,
    ) -> DriverSessionStartResult:
        """Mock 模式启动（测试路径覆盖）。"""
        session_id = str(uuid.uuid4())

        mock_session = CodexSession(
            session_id=session_id,
            prompt=task_spec.prompt,
            cwd=cwd or "",
        )

        # 模拟初始事件
        mock_session.events.append({
            "type": "system",
            "session_id": session_id,
            "message": "codex mock session started",
        })

        with self._lock:
            self._sessions[session_id] = mock_session
            self._session_tasks[session_id] = task_spec.task_id

        return DriverSessionStartResult(
            success=True,
            session_id=session_id,
            driver_name=self.driver_name,
            executor_type=self.executor_type.value,
            worktree=cwd or "",
            process_info={"mock": True},
        )

    def start_task(
        self,
        task_spec: RuntimeTaskSpec,
        cwd: Optional[str] = None,
    ) -> DriverSessionStartResult:
        """启动 Codex CLI 执行任务。"""
        if self._mock_mode:
            return self._mock_start_session(task_spec, cwd)

        session_id = str(uuid.uuid4())
        cmd = self._build_start_command(task_spec.prompt, session_id)

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                cwd=cwd,
            )

            codex_session = CodexSession(
                session_id=session_id,
                process=process,
                prompt=task_spec.prompt,
                cwd=cwd or "",
            )

            with self._lock:
                self._sessions[session_id] = codex_session
                self._session_tasks[session_id] = task_spec.task_id

            # 启动后台监控线程
            monitor = threading.Thread(
                target=self._background_monitor,
                args=(session_id,),
                daemon=True,
            )
            monitor.start()

            return DriverSessionStartResult(
                success=True,
                session_id=session_id,
                driver_name=self.driver_name,
                executor_type=self.executor_type.value,
                worktree=cwd or "",
                process_info={"pid": process.pid},
            )

        except FileNotFoundError:
            return DriverSessionStartResult(
                success=False,
                reason_code="driver_not_installed",
                reason=f"codex CLI 未安装: {self.CODEX_CMD}",
                driver_name=self.driver_name,
                executor_type=self.executor_type.value,
            )

        except Exception as exc:
            return DriverSessionStartResult(
                success=False,
                reason_code="driver_start_failed",
                reason=str(exc),
                driver_name=self.driver_name,
                executor_type=self.executor_type.value,
            )

    def _background_monitor(self, session_id: str) -> None:
        """后台监控线程（宿主细节封装）。"""
        session = self._sessions.get(session_id)
        if not session or not session.process:
            return

        try:
            for line in session.process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = self._parse_event_line(line)
                    if event:
                        session.events.append(event)
                        if event.get("type") == "result":
                            break
                except Exception:
                    continue
        except Exception:
            pass

    def _parse_event_line(self, line: str) -> Optional[Dict[str, Any]]:
        """解析事件行（宿主细节封装）。"""
        import json
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def intervene(self, session_id: str, prompt: str) -> bool:
        """干预 Codex 会话。"""
        if self._mock_mode:
            with self._lock:
                if session_id in self._sessions:
                    self._sessions[session_id].events.append({
                        "type": "intervention",
                        "prompt": prompt,
                    })
            return True

        try:
            cmd = self._build_intervene_command(session_id, prompt)
            session = self._sessions.get(session_id)
            cwd = session.cwd if session else None

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                cwd=cwd,
            )

            if session_id in self._sessions:
                self._sessions[session_id].process = process

            return True
        except Exception:
            return False

    def cancel(self, session_id: str) -> bool:
        """取消 Codex 会话。"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.process and session.process.poll() is None:
                session.process.terminate()

            if session_id in self._sessions:
                self._sessions[session_id].events.append({
                    "type": "cancelled",
                    "reason": "user_cancel",
                })

            if session_id in self._session_states:
                self._session_states[session_id].status = DriverStatus.CANCELLED

            return True

    _session_states: Dict[str, DriverSessionState] = {}

    def get_session(self, session_id: str) -> Optional[DriverSessionState]:
        """获取会话状态。"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            task_id = self._session_tasks.get(session_id, "")
            state = DriverSessionState(
                session_id=session_id,
                task_id=task_id,
                executor_type=self.executor_type.value,
                driver_name=self.driver_name,
                worktree=session.cwd,
                status=self._infer_status(session),
                prompt=session.prompt,
                started_at=session.started_at,
                events_count=len(session.events),
                last_event_type=session.events[-1].get("type", "") if session.events else "",
            )
            return state

    def _infer_status(self, session: CodexSession) -> DriverStatus:
        """推断会话状态。"""
        for event in session.events:
            if event.get("type") == "result":
                subtype = event.get("subtype", "")
                if subtype == "success":
                    return DriverStatus.COMPLETED
                elif subtype == "error":
                    return DriverStatus.FAILED
            if event.get("type") == "cancelled":
                return DriverStatus.CANCELLED

        if session.process and session.process.poll() is None:
            return DriverStatus.RUNNING

        return DriverStatus.PENDING

    def get_status(self, session_id: str) -> DriverStatus:
        """获取会话状态枚举。"""
        state = self.get_session(session_id)
        return state.status if state else DriverStatus.PENDING

    def collect_events(self, session_id: str) -> List[Dict[str, Any]]:
        """收集会话事件。"""
        with self._lock:
            session = self._sessions.get(session_id)
            return list(session.events) if session else []

    def collect_result(self, session_id: str) -> DriverExecutionResult:
        """收集执行结果。"""
        with self._lock:
            session = self._sessions.get(session_id)
            task_id = self._session_tasks.get(session_id, "")

        if not session:
            return DriverExecutionResult(
                success=False,
                session_id=session_id,
                task_id=task_id,
                executor_type=self.executor_type.value,
                driver_name=self.driver_name,
                reason_code="session_not_found",
                reason=f"会话不存在: {session_id}",
            )

        status = self._infer_status(session)
        summary = ""
        changed_files: List[str] = []
        tests: Dict[str, Any] = {}
        known_issues: List[str] = []
        test_evidence: List[str] = []

        for event in session.events:
            if event.get("type") == "result":
                summary = event.get("result", "") or event.get("summary", "")

            if event.get("type") == "assistant":
                content = event.get("message", {}).get("content", [])
                for item in content:
                    if item.get("type") == "tool_use":
                        tool_name = item.get("name", "")
                        tool_input = item.get("input", {})

                        if tool_name in ("Edit", "Write"):
                            file_path = tool_input.get("file_path", "")
                            if file_path:
                                changed_files.append(file_path)

                        if tool_name == "Bash":
                            cmd = tool_input.get("command", "")
                            if "test" in cmd.lower():
                                test_evidence.append(cmd)

        return DriverExecutionResult(
            success=status == DriverStatus.COMPLETED,
            session_id=session_id,
            task_id=task_id,
            executor_type=self.executor_type.value,
            driver_name=self.driver_name,
            summary=summary,
            changed_files=changed_files,
            tests=tests,
            known_issues=known_issues,
            test_evidence=test_evidence,
            raw_events=session.events,
        )