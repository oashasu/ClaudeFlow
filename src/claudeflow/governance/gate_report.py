"""T204: Gate Report Writer — Phase 级质量门禁报告生成。

职责:
- 统计 phase 内所有任务的 review 状态
- 生成 gate report 落盘到 phase 根目录
- 计算 advance_allowed 与 reopen_required

验收标准 A25:
- phase 级 gate report 能统计 accepted / rework / blocker 状态
- 可给出 advance_allowed / reopen_required

关键约束:
- gate report 必须落盘到 phase 根目录
- advance_allowed 与 reopen_required 必须有明确来源

Gate Report 路径:
.super-dev/phases/<phase-id>/gate-report.md

Gate Report 结构:
- phase_id
- gate_status
- accepted_tasks
- rework_required_tasks
- blocker_count
- advance_allowed
- reopen_required
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from claudeflow.governance.pipeline_state import PipelineStateStore, PipelineState
from claudeflow.governance.review_artifact import ReviewArtifact, ReviewArtifactWriter


@dataclass
class GateReport:
    """Phase 级 Gate Report 结构。"""

    phase_id: str
    gate_status: str  # open | passed | failed
    accepted_tasks: List[str] = field(default_factory=list)
    rework_required_tasks: List[str] = field(default_factory=list)
    blocker_count: int = 0
    advance_allowed: bool = False
    reopen_required: bool = False
    generated_at: str = ""
    summary: Optional[str] = None

    def to_markdown(self) -> str:
        """生成 Markdown 格式。"""
        lines = [
            f"# Gate Report: {self.phase_id}",
            "",
            f"**Gate Status**: {self.gate_status}",
            f"**Generated At**: {self.generated_at}",
            "",
            "## Summary",
            "",
            f"- **Accepted Tasks**: {len(self.accepted_tasks)}",
            f"- **Rework Required**: {len(self.rework_required_tasks)}",
            f"- **Total Blockers**: {self.blocker_count}",
            "",
            f"- **Advance Allowed**: `{self.advance_allowed}`",
            f"- **Reopen Required**: `{self.reopen_required}`",
            "",
            "## Accepted Tasks",
            "",
        ]

        if self.accepted_tasks:
            for task_id in self.accepted_tasks:
                lines.append(f"- {task_id}")
        else:
            lines.append("- *None*")

        lines.extend([
            "",
            "## Rework Required Tasks",
            "",
        ])

        if self.rework_required_tasks:
            for task_id in self.rework_required_tasks:
                lines.append(f"- {task_id}")
        else:
            lines.append("- *None*")

        if self.summary:
            lines.extend([
                "",
                "## Notes",
                "",
                self.summary,
            ])

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """生成字典格式。"""
        return {
            "phase_id": self.phase_id,
            "gate_status": self.gate_status,
            "accepted_tasks": self.accepted_tasks,
            "rework_required_tasks": self.rework_required_tasks,
            "blocker_count": self.blocker_count,
            "advance_allowed": self.advance_allowed,
            "reopen_required": self.reopen_required,
            "generated_at": self.generated_at,
            "summary": self.summary,
        }


class GateReportWriter:
    """Gate Report 写入器。"""

    REPORT_FILE = "gate-report.md"

    def __init__(
        self,
        governance_root: str | Path,
        pipeline_state_path: str | Path | None = None,
    ) -> None:
        self.governance_root = Path(governance_root)
        if pipeline_state_path is None:
            pipeline_state_path = self.governance_root / "pipeline-state.json"
        self.pipeline_store = PipelineStateStore(pipeline_state_path)
        self.review_writer = ReviewArtifactWriter(governance_root)

    def _get_phase_dir(self, phase_id: str) -> Path:
        """获取 phase 目录。"""
        return self.governance_root / "phases" / phase_id

    def _get_report_path(self, phase_id: str) -> Path:
        """获取 gate report 文件路径。"""
        return self._get_phase_dir(phase_id) / self.REPORT_FILE

    def _load_task_reviews(self, phase_id: str, task_ids: List[str]) -> Dict[str, Optional[ReviewArtifact]]:
        """加载 phase 内所有任务的 review artifacts。"""
        reviews = {}
        for task_id in task_ids:
            artifact = self.review_writer.read(phase_id, task_id)
            reviews[task_id] = artifact
        return reviews

    def generate(self, phase_id: str) -> GateReport:
        """从 pipeline-state 和 review artifacts 生成 Gate Report。

        Args:
            phase_id: 阶段 ID

        Returns:
            GateReport
        """
        # 加载 pipeline-state
        state, errors = self.pipeline_store.load()
        if errors:
            # 创建最小状态
            state = PipelineState(raw={
                "workflow_version": "v1",
                "project": "claudeflow",
                "phases": {},
                "tasks": {},
            })

        # 获取 phase 内任务
        phase_data = state.raw.get("phases", {}).get(phase_id, {})
        task_ids = []

        # 从 phase.pending_tasks 和 phase.completed_tasks 获取任务列表
        pending = phase_data.get("pending_tasks", [])
        completed = phase_data.get("completed_tasks", [])
        task_ids = list(set(pending + completed))

        # 从 tasks 字段补充任务
        tasks_data = state.raw.get("tasks", {})
        for task_id, task_data in tasks_data.items():
            if task_data.get("phase_id") == phase_id and task_id not in task_ids:
                task_ids.append(task_id)

        # 加载所有 review artifacts
        reviews = self._load_task_reviews(phase_id, task_ids)

        # 统计状态
        accepted_tasks = []
        rework_required_tasks = []
        total_blockers = 0

        for task_id in task_ids:
            artifact = reviews.get(task_id)
            task_data = tasks_data.get(task_id, {})

            # 从 review artifact 或 pipeline-state 获取状态
            if artifact:
                if artifact.decision == "accepted":
                    accepted_tasks.append(task_id)
                elif artifact.decision == "rework_required":
                    rework_required_tasks.append(task_id)
                    total_blockers += len(artifact.blocker_findings)
            else:
                # 没有 review artifact，从 pipeline-state 推断
                review_status = task_data.get("review_status", "pending")
                if review_status == "accepted":
                    accepted_tasks.append(task_id)
                elif review_status == "rework_required":
                    rework_required_tasks.append(task_id)

        # 计算 gate_status
        # 无任务时为 open
        if len(task_ids) == 0:
            gate_status = "open"
        elif len(rework_required_tasks) == 0 and len(accepted_tasks) == len(task_ids):
            gate_status = "passed"
        elif len(accepted_tasks) > 0:
            gate_status = "partial"
        else:
            gate_status = "failed"

        # 计算 advance_allowed 和 reopen_required
        # 无任务时不可推进
        advance_allowed = len(task_ids) > 0 and len(rework_required_tasks) == 0 and len(accepted_tasks) == len(task_ids)
        reopen_required = len(rework_required_tasks) > 0 or total_blockers > 0

        # 生成 summary
        summary = None
        if advance_allowed:
            summary = f"All {len(accepted_tasks)} tasks passed review. Phase can advance."
        elif reopen_required:
            summary = f"Found {len(rework_required_tasks)} tasks requiring rework with {total_blockers} blockers. Phase needs reopening."
        elif gate_status == "partial":
            summary = f"{len(accepted_tasks)} tasks accepted, {len(rework_required_tasks)} need rework."

        return GateReport(
            phase_id=phase_id,
            gate_status=gate_status,
            accepted_tasks=accepted_tasks,
            rework_required_tasks=rework_required_tasks,
            blocker_count=total_blockers,
            advance_allowed=advance_allowed,
            reopen_required=reopen_required,
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
        )

    def write(self, report: GateReport) -> Path:
        """原子写入 Gate Report 到 Markdown 文件。

        Args:
            report: GateReport

        Returns:
            写入的文件路径
        """
        target_path = self._get_report_path(report.phase_id)

        # 确保目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 生成 Markdown 内容
        content = report.to_markdown()

        # 原子写入
        fd, tmp_path = tempfile.mkstemp(
            dir=str(target_path.parent),
            prefix=".gate-report-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(target_path))
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

        return target_path

    def generate_and_write(self, phase_id: str) -> tuple[GateReport, Path]:
        """生成并写入 Gate Report。

        Returns:
            (report, path)
        """
        report = self.generate(phase_id)
        path = self.write(report)
        return report, path

    def read(self, phase_id: str) -> Optional[GateReport]:
        """读取已存在的 Gate Report。

        Args:
            phase_id: 阶段 ID

        Returns:
            GateReport 或 None
        """
        report_path = self._get_report_path(phase_id)
        if not report_path.exists():
            return None

        content = report_path.read_text(encoding="utf-8")
        return self._parse_markdown(content, phase_id)

    def _parse_markdown(self, content: str, phase_id: str) -> GateReport:
        """从 Markdown 内容解析 Gate Report。"""
        # 简单解析关键字段
        gate_status = "open"
        accepted_tasks = []
        rework_required_tasks = []
        blocker_count = 0
        advance_allowed = False
        reopen_required = False
        generated_at = ""
        summary = None

        lines = content.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            # 解析 Gate Status
            if line.startswith("**Gate Status**:"):
                gate_status = line.split(":")[1].strip()

            # 解析 Generated At
            if line.startswith("**Generated At**:"):
                generated_at = line.split(":")[1].strip()

            # 解析统计数据
            if "- **Accepted Tasks**:" in line:
                count_str = line.split(":")[1].strip()
                try:
                    # 这个是数量，不是列表
                    pass
                except ValueError:
                    pass

            if "- **Advance Allowed**:" in line:
                val = line.split(":")[1].strip().replace("`", "").lower()
                advance_allowed = val == "true"

            if "- **Reopen Required**:" in line:
                val = line.split(":")[1].strip().replace("`", "").lower()
                reopen_required = val == "true"

            # 解析 Accepted Tasks 列表
            if "## Accepted Tasks" in line:
                current_section = "accepted"
            elif "## Rework Required Tasks" in line:
                current_section = "rework"
            elif "## Notes" in line:
                current_section = "notes"
            elif line.startswith("- ") and current_section:
                task_id = line[2:].strip()
                if task_id != "*None*":
                    if current_section == "accepted":
                        accepted_tasks.append(task_id)
                    elif current_section == "rework":
                        rework_required_tasks.append(task_id)
                    elif current_section == "notes":
                        summary = task_id

        return GateReport(
            phase_id=phase_id,
            gate_status=gate_status,
            accepted_tasks=accepted_tasks,
            rework_required_tasks=rework_required_tasks,
            blocker_count=blocker_count,
            advance_allowed=advance_allowed,
            reopen_required=reopen_required,
            generated_at=generated_at,
            summary=summary,
        )

    def update_pipeline_state(self, report: GateReport) -> None:
        """根据 Gate Report 更新 pipeline-state.json。

        同步全局状态 current_stage/current_gate 与 phase 状态，确保状态机一致性。

        Args:
            report: GateReport
        """
        state, _ = self.pipeline_store.load()

        # 更新 phase 状态
        phases = state.raw.get("phases", {})
        phase_data = phases.get(report.phase_id, {})

        phase_data["gate_status"] = report.gate_status
        phase_data["advance_allowed"] = report.advance_allowed
        phase_data["reopen_required"] = report.reopen_required
        phase_data["quality_gate_passed"] = report.advance_allowed

        if report.advance_allowed:
            phase_data["status"] = "accepted"

        phases[report.phase_id] = phase_data
        state.raw["phases"] = phases

        # 更新全局 gate_status
        state.raw["gate_status"] = report.gate_status
        state.raw["advance_allowed"] = report.advance_allowed
        state.raw["reopen_required"] = report.reopen_required

        # 收敛全局 workflow 状态：phase accepted 时同步 current_stage/current_gate
        if report.advance_allowed:
            state.raw["current_stage"] = "accepted"
            state.raw["current_gate"] = ""
        elif report.reopen_required:
            state.raw["current_stage"] = "reopened"
            state.raw["current_gate"] = "implementation_review"

        self.pipeline_store.save(state)