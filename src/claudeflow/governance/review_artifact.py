"""T201: Review Artifact 模型与写入能力。

职责:
- 定义 review artifact 数据结构
- 写入 .super-dev/phases/<phase-id>/reviews/<task-id>-review.md
- 标准化 decision 和 findings 结构

Spec 来源: Phase 2 spec.md

关键约束:
- review artifact 必须落盘到 phase reviews 目录
- 不得只在内存中保留审查结论
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VALID_DECISIONS = ("accepted", "rework_required")

VALID_REVIEW_STATUSES = ("pending", "in_review", "passed", "failed")


@dataclass
class Finding:
    """审查发现（blocker 或 non-blocker）。"""

    severity: str  # "blocker" | "non_blocker"
    category: str  # 分类: "logic", "security", "performance", "style", etc.
    description: str
    location: Optional[str] = None  # 文件路径或代码位置
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "location": self.location,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class AcceptanceResult:
    """验收项结果。"""

    acceptance_id: str
    passed: bool
    evidence: Optional[str] = None  # 测试文件、日志等证据
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "acceptance_id": self.acceptance_id,
            "passed": self.passed,
            "evidence": self.evidence,
            "notes": self.notes,
        }


@dataclass
class ReviewArtifact:
    """审查产物结构。"""

    task_id: str
    phase_id: str
    review_status: str = "pending"
    decision: str = "pending"  # accepted | rework_required | pending
    blocker_findings: List[Finding] = field(default_factory=list)
    non_blocker_findings: List[Finding] = field(default_factory=list)
    acceptance_results: List[AcceptanceResult] = field(default_factory=list)
    reviewer_host: Optional[str] = None
    reviewed_at: Optional[str] = None
    summary: Optional[str] = None

    def __post_init__(self) -> None:
        if self.review_status not in VALID_REVIEW_STATUSES:
            raise ValueError(f"非法 review_status: {self.review_status}")
        if self.decision not in VALID_DECISIONS and self.decision != "pending":
            raise ValueError(f"非法 decision: {self.decision}")

    def has_blockers(self) -> bool:
        return len(self.blocker_findings) > 0

    def all_acceptance_passed(self) -> bool:
        return all(ar.passed for ar in self.acceptance_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "phase_id": self.phase_id,
            "review_status": self.review_status,
            "decision": self.decision,
            "blocker_findings": [f.to_dict() for f in self.blocker_findings],
            "non_blocker_findings": [f.to_dict() for f in self.non_blocker_findings],
            "acceptance_results": [ar.to_dict() for ar in self.acceptance_results],
            "reviewer_host": self.reviewer_host,
            "reviewed_at": self.reviewed_at,
            "summary": self.summary,
        }

    def to_markdown(self) -> str:
        """生成 review artifact 的 Markdown 格式。"""
        lines = [
            f"# Review Artifact: {self.task_id}",
            "",
            f"**Phase**: {self.phase_id}",
            f"**Review Status**: {self.review_status}",
            f"**Decision**: {self.decision}",
            "",
        ]

        if self.summary:
            lines.extend([
                "## Summary",
                "",
                self.summary,
                "",
            ])

        if self.blocker_findings:
            lines.extend([
                "## Blocker Findings",
                "",
            ])
            for i, f in enumerate(self.blocker_findings, 1):
                lines.extend([
                    f"### B{i}. [{f.category}] {f.location or 'General'}",
                    "",
                    f"**Description**: {f.description}",
                    "",
                ])
                if f.suggested_fix:
                    lines.extend([
                        f"**Suggested Fix**: {f.suggested_fix}",
                        "",
                    ])

        if self.non_blocker_findings:
            lines.extend([
                "## Non-Blocker Findings",
                "",
            ])
            for i, f in enumerate(self.non_blocker_findings, 1):
                lines.extend([
                    f"### N{i}. [{f.category}] {f.location or 'General'}",
                    "",
                    f"**Description**: {f.description}",
                    "",
                ])
                if f.suggested_fix:
                    lines.extend([
                        f"**Suggested Fix**: {f.suggested_fix}",
                        "",
                    ])

        if self.acceptance_results:
            lines.extend([
                "## Acceptance Results",
                "",
            ])
            for ar in self.acceptance_results:
                status = "PASS" if ar.passed else "FAIL"
                lines.extend([
                    f"- **{ar.acceptance_id}**: {status}",
                    "",
                ])
                if ar.evidence:
                    lines.extend([
                        f"  - Evidence: {ar.evidence}",
                        "",
                    ])
                if ar.notes:
                    lines.extend([
                        f"  - Notes: {ar.notes}",
                        "",
                    ])

        lines.extend([
            "---",
            "",
            f"*Reviewed by {self.reviewer_host or 'governor'} at {self.reviewed_at or 'N/A'}*",
        ])

        return "\n".join(lines)


class ReviewArtifactWriter:
    """Review Artifact 写入器。"""

    def __init__(self, governance_root: str | Path) -> None:
        self.governance_root = Path(governance_root)

    def get_review_path(self, phase_id: str, task_id: str) -> Path:
        """获取 review artifact 的目标路径。"""
        return self.governance_root / "phases" / phase_id / "reviews" / f"{task_id}-review.md"

    def write(self, artifact: ReviewArtifact) -> Path:
        """原子写入 review artifact 到目标路径。

        返回写入的文件路径。
        """
        target_path = self.get_review_path(artifact.phase_id, artifact.task_id)

        # 确保目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 更新时间戳
        artifact.reviewed_at = datetime.now(timezone.utc).isoformat()

        # 生成 Markdown 内容
        content = artifact.to_markdown()

        # 原子写入：先写临时文件再替换
        fd, tmp_path = tempfile.mkstemp(
            dir=str(target_path.parent),
            prefix=f".{artifact.task_id}-review-",
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

    def read(self, phase_id: str, task_id: str) -> Optional[ReviewArtifact]:
        """读取已有的 review artifact（如果存在）。"""
        target_path = self.get_review_path(phase_id, task_id)
        if not target_path.exists():
            return None

        content = target_path.read_text(encoding="utf-8")
        return self._parse_markdown(content)

    def _parse_markdown(self, content: str) -> ReviewArtifact:
        """从 Markdown 内容解析 ReviewArtifact。

        简化解析：只提取关键结构信息。
        """
        lines = content.split("\n")

        task_id = ""
        phase_id = ""
        review_status = "pending"
        decision = "pending"
        blocker_findings: List[Finding] = []
        non_blocker_findings: List[Finding] = []
        acceptance_results: List[AcceptanceResult] = []
        reviewer_host = None
        reviewed_at = None
        summary = None

        current_section = ""
        current_finding_severity = ""

        for line in lines:
            if line.startswith("# Review Artifact: "):
                task_id = line.split(": ")[1].strip()
            elif line.startswith("**Phase**: "):
                phase_id = line.split(": ")[1].strip()
            elif line.startswith("**Review Status**: "):
                review_status = line.split(": ")[1].strip()
            elif line.startswith("**Decision**: "):
                decision = line.split(": ")[1].strip()
            elif line.startswith("**Reviewer**: ") or line.startswith("*Reviewed by "):
                reviewer_host = line.split("by ")[1].split(" at ")[0].strip()
                if " at " in line:
                    reviewed_at = line.split(" at ")[1].rstrip("*").strip()
            elif line.startswith("## Summary"):
                current_section = "summary"
            elif line.startswith("## Blocker Findings"):
                current_section = "findings"
                current_finding_severity = "blocker"
            elif line.startswith("## Non-Blocker Findings"):
                current_section = "findings"
                current_finding_severity = "non_blocker"
            elif line.startswith("## Acceptance Results"):
                current_section = "acceptance"
            elif line.startswith("### ") and current_section == "findings":
                # 解析 finding header: ### B1. [category] location
                parts = line[4:].split(" ", 1)
                if "[" in parts[1]:
                    category = parts[1].split("[")[1].split("]")[0]
                    location = parts[1].split("] ")[1] if "] " in parts[1] else None
                    finding = Finding(
                        severity=current_finding_severity,
                        category=category,
                        description="",  # 后续行填充
                        location=location,
                    )
                    if current_finding_severity == "blocker":
                        blocker_findings.append(finding)
                    else:
                        non_blocker_findings.append(finding)
            elif line.startswith("**Description**: ") and current_section == "findings":
                desc = line.split(": ")[1].strip()
                if current_finding_severity == "blocker" and blocker_findings:
                    blocker_findings[-1].description = desc
                elif non_blocker_findings:
                    non_blocker_findings[-1].description = desc
            elif line.startswith("**Suggested Fix**: ") and current_section == "findings":
                fix = line.split(": ")[1].strip()
                if current_finding_severity == "blocker" and blocker_findings:
                    blocker_findings[-1].suggested_fix = fix
                elif non_blocker_findings:
                    non_blocker_findings[-1].suggested_fix = fix
            elif line.startswith("- **") and current_section == "acceptance":
                # 解析 acceptance: - **A21**: PASS
                parts = line[4:].split(": ")
                acc_id = parts[0].rstrip("**").strip()
                passed = parts[1].strip() == "PASS"
                acceptance_results.append(AcceptanceResult(
                    acceptance_id=acc_id,
                    passed=passed,
                ))
            elif current_section == "summary" and line.strip() and not line.startswith("##"):
                summary = (summary or "") + line + "\n"

        return ReviewArtifact(
            task_id=task_id,
            phase_id=phase_id,
            review_status=review_status,
            decision=decision,
            blocker_findings=blocker_findings,
            non_blocker_findings=non_blocker_findings,
            acceptance_results=acceptance_results,
            reviewer_host=reviewer_host,
            reviewed_at=reviewed_at,
            summary=summary.strip() if summary else None,
        )

    def exists(self, phase_id: str, task_id: str) -> bool:
        """检查 review artifact 是否已存在。"""
        return self.get_review_path(phase_id, task_id).exists()