"""T202: Review Queue — Worker 结果回收到 review-ready 状态。

职责:
- 接收 Worker 已完成结果
- 生成待审查索引或队列对象
- 回写 pipeline-state.json
- 保证 Governor 有稳定输入

验收标准 A22:
- Worker 结果回收后进入 submitted 或 under_review
- pipeline-state.json 可见状态变化

关键约束:
- 必须回写 pipeline-state.json
- 不得绕开现有 RuntimeManager 结果回收路径
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claudeflow.governance.pipeline_state import (
    PipelineState,
    PipelineStateStore,
    PipelineStateError,
    VALID_TASK_STATUSES,
)


@dataclass
class ReviewQueueEntry:
    """待审查任务条目。"""

    task_id: str
    phase_id: str
    executor_type: str
    status: str  # submitted | under_review
    submitted_at: str
    summary: Optional[str] = None
    changed_files: List[str] = field(default_factory=list)
    tests: Dict[str, Any] = field(default_factory=dict)
    known_issues: List[str] = field(default_factory=list)
    test_evidence: List[str] = field(default_factory=list)
    driver_name: Optional[str] = None
    worktree: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "phase_id": self.phase_id,
            "executor_type": self.executor_type,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "summary": self.summary,
            "changed_files": self.changed_files,
            "tests": self.tests,
            "known_issues": self.known_issues,
            "test_evidence": self.test_evidence,
            "driver_name": self.driver_name,
            "worktree": self.worktree,
        }


@dataclass
class ReviewQueueIndex:
    """Review Queue 索引文件。"""

    entries: List[ReviewQueueEntry] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "updated_at": self.updated_at,
        }


class ReviewQueue:
    """Review Queue 管理。"""

    QUEUE_FILE = "review-queue.json"

    def __init__(
        self,
        governance_root: str | Path,
        pipeline_state_path: str | Path | None = None,
    ) -> None:
        self.governance_root = Path(governance_root)
        if pipeline_state_path is None:
            pipeline_state_path = self.governance_root / "pipeline-state.json"
        self.pipeline_store = PipelineStateStore(pipeline_state_path)

    def _get_queue_path(self) -> Path:
        """获取 queue 索引文件路径。"""
        return self.governance_root / self.QUEUE_FILE

    def submit_result(
        self,
        task_id: str,
        phase_id: str,
        executor_type: str,
        summary: Optional[str] = None,
        changed_files: Optional[List[str]] = None,
        tests: Optional[Dict[str, Any]] = None,
        known_issues: Optional[List[str]] = None,
        test_evidence: Optional[List[str]] = None,
        driver_name: Optional[str] = None,
        worktree: Optional[str] = None,
    ) -> ReviewQueueEntry:
        """提交任务结果到 Review Queue。

        步骤:
        1. 创建 ReviewQueueEntry
        2. 更新 pipeline-state.json
        3. 更新 review-queue.json 索引

        Args:
            task_id: 任务 ID
            phase_id: 阶段 ID
            executor_type: 执行器类型
            summary: 任务摘要
            changed_files: 变更文件列表
            tests: 测试结果
            known_issues: 已知问题
            test_evidence: 测试证据
            driver_name: 驱动名称
            worktree: 工作树路径

        Returns:
            ReviewQueueEntry
        """
        now = datetime.now(timezone.utc).isoformat()

        entry = ReviewQueueEntry(
            task_id=task_id,
            phase_id=phase_id,
            executor_type=executor_type,
            status="submitted",
            submitted_at=now,
            summary=summary,
            changed_files=changed_files or [],
            tests=tests or {},
            known_issues=known_issues or [],
            test_evidence=test_evidence or [],
            driver_name=driver_name,
            worktree=worktree,
        )

        # 1. 更新 pipeline-state.json
        self._update_pipeline_state(task_id, phase_id, entry)

        # 2. 更新 review-queue.json 索引
        self._add_to_queue_index(entry)

        return entry

    def submit_from_runtime_result(
        self,
        runtime_result: Dict[str, Any],
        phase_id: str,
        worktree: Optional[str] = None,
    ) -> ReviewQueueEntry:
        """从 RuntimeManager.collect_session_result() 结果创建条目。

        Args:
            runtime_result: RuntimeManager.collect_session_result() 返回的结果
            phase_id: 阶段 ID
            worktree: 工作树路径

        Returns:
            ReviewQueueEntry
        """
        return self.submit_result(
            task_id=runtime_result.get("task_id", ""),
            phase_id=phase_id,
            executor_type=runtime_result.get("executor_type", "claude"),
            summary=runtime_result.get("summary"),
            changed_files=runtime_result.get("changed_files"),
            tests=runtime_result.get("tests"),
            known_issues=runtime_result.get("known_issues"),
            test_evidence=runtime_result.get("test_evidence"),
            driver_name=runtime_result.get("driver_name"),
            worktree=worktree,
        )

    def _update_pipeline_state(
        self,
        task_id: str,
        phase_id: str,
        entry: ReviewQueueEntry,
    ) -> None:
        """更新 pipeline-state.json 中任务状态为 submitted。"""
        state, errors = self.pipeline_store.load()
        if errors:
            # 如果加载失败，尝试创建最小状态
            # 注意：Governor 宿主默认为 codex，符合治理角色边界
            state = PipelineState(raw={
                "workflow_version": "v1",
                "project": "claudeflow",
                "current_phase": phase_id,
                "current_stage": "implementation_review",
                "current_gate": "implementation_review",
                "gate_status": "open",
                "governor": {"host": "codex", "mode": "governor"},
                "advance_allowed": False,
                "reopen_required": False,
                "phases": {},
                "tasks": {},
                "timestamps": {"updated_at": ""},
            })

        # 更新任务状态
        tasks = state.raw.get("tasks", {})
        if task_id in tasks:
            tasks[task_id]["status"] = "submitted"
            tasks[task_id]["review_status"] = "pending"
            tasks[task_id]["submitted_at"] = entry.submitted_at
            if entry.summary:
                tasks[task_id]["summary"] = entry.summary
            if entry.changed_files:
                tasks[task_id]["changed_files"] = entry.changed_files
            if entry.tests:
                tasks[task_id]["tests"] = entry.tests
        else:
            # 创建新任务条目
            tasks[task_id] = {
                "phase_id": phase_id,
                "executor_type": entry.executor_type,
                "status": "submitted",
                "review_status": "pending",
                "submitted_at": entry.submitted_at,
                "summary": entry.summary or "",
                "changed_files": entry.changed_files,
                "tests": entry.tests,
            }

        state.raw["tasks"] = tasks

        # 更新 phase 状态
        phases = state.raw.get("phases", {})
        if phase_id not in phases:
            phases[phase_id] = {
                "status": "implementation_review",
                "docs_ready": True,
                "tasks_ready": True,
                "quality_gate_passed": False,
                "completed_tasks": [],
                "pending_tasks": [],
            }

        # 确保 pending_tasks 包含此任务
        pending = phases[phase_id].get("pending_tasks", [])
        if task_id not in pending:
            pending.append(task_id)
        phases[phase_id]["pending_tasks"] = pending

        state.raw["phases"] = phases
        state.raw["current_stage"] = "implementation_review"
        state.raw["current_gate"] = "implementation_review"

        self.pipeline_store.save(state)

    def _add_to_queue_index(self, entry: ReviewQueueEntry) -> None:
        """添加条目到 review-queue.json 索引。"""
        queue_path = self._get_queue_path()

        # 加载现有索引
        index = self._load_queue_index()

        # 移除同名旧条目（如果有）
        index.entries = [e for e in index.entries if e.task_id != entry.task_id]

        # 添加新条目
        index.entries.append(entry)
        index.updated_at = datetime.now(timezone.utc).isoformat()

        # 原子写入
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(index.to_dict(), ensure_ascii=False, indent=2)

        fd, tmp_path = tempfile.mkstemp(
            dir=str(queue_path.parent),
            prefix=".review-queue-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_path, str(queue_path))
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def _load_queue_index(self) -> ReviewQueueIndex:
        """加载 review-queue.json 索引。"""
        queue_path = self._get_queue_path()
        if not queue_path.exists():
            return ReviewQueueIndex()

        try:
            raw = json.loads(queue_path.read_text(encoding="utf-8"))
            entries = [
                ReviewQueueEntry(**e)
                for e in raw.get("entries", [])
            ]
            return ReviewQueueIndex(
                entries=entries,
                updated_at=raw.get("updated_at", ""),
            )
        except (json.JSONDecodeError, TypeError):
            return ReviewQueueIndex()

    def get_pending_reviews(self) -> List[ReviewQueueEntry]:
        """获取所有待审查任务。"""
        index = self._load_queue_index()
        return [e for e in index.entries if e.status in ("submitted", "under_review")]

    def get_entry(self, task_id: str) -> Optional[ReviewQueueEntry]:
        """获取指定任务的审查条目。"""
        index = self._load_queue_index()
        for entry in index.entries:
            if entry.task_id == task_id:
                return entry
        return None

    def mark_under_review(self, task_id: str) -> Optional[ReviewQueueEntry]:
        """将任务标记为 under_review 状态。"""
        entry = self.get_entry(task_id)
        if entry is None:
            return None

        entry.status = "under_review"
        self._add_to_queue_index(entry)

        # 同时更新 pipeline-state.json
        state, _ = self.pipeline_store.load()
        if task_id in state.raw.get("tasks", {}):
            state.raw["tasks"][task_id]["review_status"] = "in_review"
            self.pipeline_store.save(state)

        return entry

    def remove_from_queue(self, task_id: str) -> bool:
        """从队列中移除任务（审查完成后）。"""
        index = self._load_queue_index()
        original_count = len(index.entries)
        index.entries = [e for e in index.entries if e.task_id != task_id]

        if len(index.entries) == original_count:
            return False

        index.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_queue_index(index)
        return True

    def _save_queue_index(self, index: ReviewQueueIndex) -> None:
        """保存 queue 索引。"""
        queue_path = self._get_queue_path()
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(index.to_dict(), ensure_ascii=False, indent=2)

        fd, tmp_path = tempfile.mkstemp(
            dir=str(queue_path.parent),
            prefix=".review-queue-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp_path, str(queue_path))
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise