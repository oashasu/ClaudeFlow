"""T205: Phase Gate Service — Phase reopen 与 advance 状态管理。

职责:
- 管理 phase 状态转换
- 处理 accepted 路径（任务进入 accepted）
- 处理 rework_required 路径（phase reopen）
- 基于 gate report 决定 advance 或 reopen

验收标准 A24:
- review 判定 accepted 后原任务进入 accepted
- 不生成多余 rework task

验收标准 A26:
- 全部通过时 phase 可推进
- 存在 blocker 或返工时 phase 不得推进，并可 reopen

关键约束:
- 不得在无 gate report 的情况下推进 phase
- 不得让 review fail 仍然保持 advance_allowed=true

状态流转:

task.status:
  implementing → submitted → under_review → accepted
  implementing → submitted → under_review → rework_required

phase.status:
  in_execution → implementation_review → quality_gate → accepted
  in_execution → implementation_review → reopened
"""

from __future__ import annotations

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
    VALID_PHASE_STATUSES,
    VALID_TASK_STATUSES,
)
from claudeflow.governance.gate_report import GateReport, GateReportWriter
from claudeflow.governance.review_artifact import ReviewArtifact, ReviewArtifactWriter
from claudeflow.governance.rework_generator import ReworkTaskGenerator, ReworkTaskPackage


@dataclass
class PhaseGateResult:
    """Phase Gate 操作结果。"""

    phase_id: str
    action: str  # advance | reopen | blocked
    success: bool
    reason: str
    updated_tasks: List[str] = field(default_factory=list)
    gate_report_ref: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "action": self.action,
            "success": self.success,
            "reason": self.reason,
            "updated_tasks": self.updated_tasks,
            "gate_report_ref": self.gate_report_ref,
            "timestamp": self.timestamp,
        }


class PhaseGateService:
    """Phase Gate 状态管理服务。"""

    def __init__(
        self,
        governance_root: str | Path,
        pipeline_state_path: str | Path | None = None,
    ) -> None:
        self.governance_root = Path(governance_root)
        if pipeline_state_path is None:
            pipeline_state_path = self.governance_root / "pipeline-state.json"
        self.pipeline_store = PipelineStateStore(pipeline_state_path)
        self.gate_writer = GateReportWriter(governance_root)
        self.review_writer = ReviewArtifactWriter(governance_root)
        self.rework_generator = ReworkTaskGenerator(governance_root)

    def _get_phase_dir(self, phase_id: str) -> Path:
        """获取 phase 目录。"""
        return self.governance_root / "phases" / phase_id

    def _ensure_gate_report(self, phase_id: str) -> Optional[GateReport]:
        """确保 gate report 存在，不存在则生成。"""
        report = self.gate_writer.read(phase_id)
        if report is None:
            report = self.gate_writer.generate(phase_id)
            self.gate_writer.write(report)
        return report

    def update_task_status(
        self,
        phase_id: str,
        task_id: str,
        decision: str,
    ) -> Optional[PhaseGateResult]:
        """根据 review decision 更新任务状态。

        Args:
            phase_id: 阶段 ID
            task_id: 任务 ID
            decision: accepted | rework_required

        Returns:
            PhaseGateResult 或 None
        """
        # 验证 decision
        if decision not in ("accepted", "rework_required"):
            return None

        # 加载 pipeline-state
        state, errors = self.pipeline_store.load()
        if errors:
            return None

        # 获取 task 数据
        tasks = state.raw.get("tasks", {})
        task_data = tasks.get(task_id, {})
        if not task_data:
            return None

        # A24: accepted 路径
        if decision == "accepted":
            task_data["status"] = "accepted"
            task_data["review_status"] = "accepted"
            task_data["accepted_at"] = datetime.now(timezone.utc).isoformat()
            tasks[task_id] = task_data
            state.raw["tasks"] = tasks

            # 更新 phase completed_tasks
            phases = state.raw.get("phases", {})
            phase_data = phases.get(phase_id, {})
            completed = phase_data.get("completed_tasks", [])
            if task_id not in completed:
                completed.append(task_id)
            phase_data["completed_tasks"] = completed

            # 从 pending 移除
            pending = phase_data.get("pending_tasks", [])
            if task_id in pending:
                pending.remove(task_id)
            phase_data["pending_tasks"] = pending
            phases[phase_id] = phase_data
            state.raw["phases"] = phases

            self.pipeline_store.save(state)

            return PhaseGateResult(
                phase_id=phase_id,
                action="task_accepted",
                success=True,
                reason=f"Task {task_id} accepted",
                updated_tasks=[task_id],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # A24: rework_required 路径 - 不生成多余 rework task（由 ReworkTaskGenerator 负责）
        task_data["status"] = "rework_required"
        task_data["review_status"] = "rework_required"
        tasks[task_id] = task_data
        state.raw["tasks"] = tasks

        self.pipeline_store.save(state)

        return PhaseGateResult(
            phase_id=phase_id,
            action="task_rework_required",
            success=True,
            reason=f"Task {task_id} requires rework",
            updated_tasks=[task_id],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def can_advance_phase(self, phase_id: str) -> tuple[bool, str]:
        """检查 phase 是否可以推进。

        约束:
        - 必须有 gate report
        - gate report 显示 advance_allowed = true

        Returns:
            (can_advance, reason)
        """
        # 检查 gate report
        report = self.gate_writer.read(phase_id)
        if report is None:
            return False, "No gate report found"

        if not report.advance_allowed:
            return False, f"Gate report shows advance_allowed=false. Blockers: {report.blocker_count}, Rework: {len(report.rework_required_tasks)}"

        return True, "All tasks accepted, phase can advance"

    def advance_phase(self, phase_id: str) -> PhaseGateResult:
        """推进 phase 到 accepted 状态。

        约束:
        - 必须有 gate report 且 advance_allowed = true
        - 不得绕开 gate report 验证

        Returns:
            PhaseGateResult
        """
        # A26: 检查是否可以推进
        can_advance, reason = self.can_advance_phase(phase_id)
        if not can_advance:
            return PhaseGateResult(
                phase_id=phase_id,
                action="blocked",
                success=False,
                reason=reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # 确保最新 gate report
        report = self._ensure_gate_report(phase_id)

        # 加载 pipeline-state
        state, _ = self.pipeline_store.load()

        # A26: 全部通过时 phase 可推进
        phases = state.raw.get("phases", {})
        phase_data = phases.get(phase_id, {})
        phase_data["status"] = "accepted"
        phase_data["quality_gate_passed"] = True
        phase_data["accepted_at"] = datetime.now(timezone.utc).isoformat()
        phases[phase_id] = phase_data
        state.raw["phases"] = phases

        # 更新全局状态
        state.raw["current_stage"] = "accepted"
        state.raw["gate_status"] = "passed"
        state.raw["advance_allowed"] = True
        state.raw["reopen_required"] = False

        self.pipeline_store.save(state)

        # 更新 gate report pipeline state
        self.gate_writer.update_pipeline_state(report)

        gate_ref = f"phases/{phase_id}/gate-report.md"

        return PhaseGateResult(
            phase_id=phase_id,
            action="advance",
            success=True,
            reason="Phase advanced to accepted",
            gate_report_ref=gate_ref,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def can_reopen_phase(self, phase_id: str) -> tuple[bool, str]:
        """检查 phase 是否需要 reopen。

        Returns:
            (can_reopen, reason)
        """
        report = self.gate_writer.read(phase_id)
        if report is None:
            report = self.gate_writer.generate(phase_id)

        if report.reopen_required:
            return True, f"Found {len(report.rework_required_tasks)} rework tasks and {report.blocker_count} blockers"

        return False, "No blockers or rework tasks"

    def reopen_phase(self, phase_id: str) -> PhaseGateResult:
        """ reopen phase 到 implementation_review 状态。

        约束:
        - 存在 blocker 或返工时 phase 不得推进
        - 可 reopen 继续返工循环

        Returns:
            PhaseGateResult
        """
        # A26: 检查是否需要 reopen
        can_reopen, reason = self.can_reopen_phase(phase_id)
        if not can_reopen:
            return PhaseGateResult(
                phase_id=phase_id,
                action="blocked",
                success=False,
                reason=reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # 确保最新 gate report
        report = self._ensure_gate_report(phase_id)

        # 加载 pipeline-state
        state, _ = self.pipeline_store.load()

        # A26: 存在 blocker 或返工时 phase 进入 reopened
        phases = state.raw.get("phases", {})
        phase_data = phases.get(phase_id, {})
        phase_data["status"] = "reopened"
        phase_data["quality_gate_passed"] = False
        phase_data["reopened_at"] = datetime.now(timezone.utc).isoformat()
        phase_data["reopen_count"] = phase_data.get("reopen_count", 0) + 1
        phases[phase_id] = phase_data
        state.raw["phases"] = phases

        # 更新全局状态
        state.raw["current_stage"] = "reopened"
        state.raw["gate_status"] = "failed"
        state.raw["advance_allowed"] = False
        state.raw["reopen_required"] = True

        self.pipeline_store.save(state)

        # 更新 gate report pipeline state
        self.gate_writer.update_pipeline_state(report)

        gate_ref = f"phases/{phase_id}/gate-report.md"

        return PhaseGateResult(
            phase_id=phase_id,
            action="reopen",
            success=True,
            reason=f"Phase reopened due to {len(report.rework_required_tasks)} rework tasks",
            updated_tasks=report.rework_required_tasks,
            gate_report_ref=gate_ref,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def process_review_decision(
        self,
        phase_id: str,
        task_id: str,
        review_artifact: ReviewArtifact,
    ) -> PhaseGateResult:
        """处理 review decision 的完整流程。

        流程:
        1. 更新任务状态（A24）
        2. 如果 rework_required，生成返工任务
        3. 更新 gate report
        4. 根据 gate report 状态决定 advance 或 reopen

        Args:
            phase_id: 阶段 ID
            task_id: 任务 ID
            review_artifact: ReviewArtifact

        Returns:
            PhaseGateResult
        """
        decision = review_artifact.decision

        # A24: 更新任务状态
        task_result = self.update_task_status(phase_id, task_id, decision)
        if task_result is None:
            return PhaseGateResult(
                phase_id=phase_id,
                action="blocked",
                success=False,
                reason=f"Invalid decision: {decision}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # A24: rework_required 时生成返工任务（不生成多余）
        if decision == "rework_required":
            rework_pkg, rework_path = self.rework_generator.generate_and_write(
                review_artifact=review_artifact,
                original_task_id=task_id,
                phase_id=phase_id,
            )

        # 更新 gate report
        report = self._ensure_gate_report(phase_id)

        # 根据 gate report 决定下一步
        if report.advance_allowed:
            # 尝试推进
            return self.advance_phase(phase_id)
        elif report.reopen_required:
            # 尝试 reopen
            return self.reopen_phase(phase_id)
        else:
            # 等待更多 review
            return PhaseGateResult(
                phase_id=phase_id,
                action="pending",
                success=True,
                reason="Waiting for more reviews",
                updated_tasks=[task_id],
                gate_report_ref=f"phases/{phase_id}/gate-report.md",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def get_phase_status(self, phase_id: str) -> Dict[str, Any]:
        """获取 phase 当前状态摘要。"""
        state, _ = self.pipeline_store.load()
        phase_data = state.raw.get("phases", {}).get(phase_id, {})
        report = self.gate_writer.read(phase_id)

        return {
            "phase_id": phase_id,
            "status": phase_data.get("status", "unknown"),
            "quality_gate_passed": phase_data.get("quality_gate_passed", False),
            "completed_tasks": len(phase_data.get("completed_tasks", [])),
            "pending_tasks": len(phase_data.get("pending_tasks", [])),
            "advance_allowed": report.advance_allowed if report else False,
            "reopen_required": report.reopen_required if report else False,
            "blocker_count": report.blocker_count if report else 0,
        }