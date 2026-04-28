"""T201: Review Artifact 模型与写入能力测试。

验收标准 A21:
- Governor 审查后能生成标准化 review artifact
- 文件路径和命名可由 phase_id + task_id 稳定定位

关键约束:
- review artifact 必须落盘到 phase reviews 目录
- 不得只在内存中保留审查结论
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from claudeflow.governance.review_artifact import (
    AcceptanceResult,
    Finding,
    ReviewArtifact,
    ReviewArtifactWriter,
    VALID_DECISIONS,
    VALID_REVIEW_STATUSES,
)


@pytest.fixture
def tmp_governance_root(tmp_path):
    """创建临时治理根目录。"""
    return tmp_path / ".super-dev"


@pytest.fixture
def writer(tmp_governance_root):
    """创建 ReviewArtifactWriter。"""
    tmp_governance_root.mkdir(parents=True, exist_ok=True)
    return ReviewArtifactWriter(tmp_governance_root)


class TestFinding:
    """Finding 数据结构测试。"""

    def test_finding_creation(self):
        finding = Finding(
            severity="blocker",
            category="logic",
            description="Missing null check",
            location="src/main.py:42",
            suggested_fix="Add if x is None: return",
        )
        assert finding.severity == "blocker"
        assert finding.category == "logic"
        assert finding.description == "Missing null check"

    def test_finding_to_dict(self):
        finding = Finding(
            severity="non_blocker",
            category="style",
            description="Variable name too short",
        )
        d = finding.to_dict()
        assert d["severity"] == "non_blocker"
        assert d["category"] == "style"
        assert d["location"] is None


class TestAcceptanceResult:
    """AcceptanceResult 数据结构测试。"""

    def test_passed_result(self):
        result = AcceptanceResult(
            acceptance_id="A21",
            passed=True,
            evidence="tests/unit/test_review_artifact.py",
        )
        assert result.passed
        assert result.acceptance_id == "A21"

    def test_failed_result(self):
        result = AcceptanceResult(
            acceptance_id="A22",
            passed=False,
            notes="Missing test coverage",
        )
        assert not result.passed


class TestReviewArtifact:
    """ReviewArtifact 数据结构测试。"""

    def test_artifact_creation(self):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="in_review",
        )
        assert artifact.task_id == "T101"
        assert artifact.phase_id == "phase-1"

    def test_invalid_review_status_raises(self):
        with pytest.raises(ValueError, match="非法 review_status"):
            ReviewArtifact(
                task_id="T101",
                phase_id="phase-1",
                review_status="invalid_status",
            )

    def test_invalid_decision_raises(self):
        with pytest.raises(ValueError, match="非法 decision"):
            ReviewArtifact(
                task_id="T101",
                phase_id="phase-1",
                decision="invalid_decision",
            )

    def test_has_blockers(self):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="SQL injection"),
            ],
        )
        assert artifact.has_blockers()

    def test_no_blockers(self):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            non_blocker_findings=[
                Finding(severity="non_blocker", category="style", description="Naming"),
            ],
        )
        assert not artifact.has_blockers()

    def test_all_acceptance_passed(self):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            acceptance_results=[
                AcceptanceResult(acceptance_id="A21", passed=True),
                AcceptanceResult(acceptance_id="A22", passed=True),
            ],
        )
        assert artifact.all_acceptance_passed()

    def test_some_acceptance_failed(self):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            acceptance_results=[
                AcceptanceResult(acceptance_id="A21", passed=True),
                AcceptanceResult(acceptance_id="A22", passed=False),
            ],
        )
        assert not artifact.all_acceptance_passed()

    def test_to_dict(self):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
            reviewer_host="codex",
        )
        d = artifact.to_dict()
        assert d["task_id"] == "T101"
        assert d["decision"] == "accepted"

    def test_to_markdown(self):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
            blocker_findings=[
                Finding(
                    severity="blocker",
                    category="logic",
                    description="Bug in calculation",
                    location="src/math.py:10",
                ),
            ],
            acceptance_results=[
                AcceptanceResult(acceptance_id="A21", passed=True),
            ],
            reviewer_host="codex",
            summary="Review passed after fix",
        )
        md = artifact.to_markdown()
        assert "# Review Artifact: T101" in md
        assert "**Phase**: phase-1" in md
        assert "**Decision**: accepted" in md
        assert "## Blocker Findings" in md
        assert "## Acceptance Results" in md
        assert "A21" in md


class TestReviewArtifactWriter:
    """ReviewArtifactWriter 写入与定位测试。"""

    def test_get_review_path(self, writer, tmp_governance_root):
        path = writer.get_review_path("phase-1", "T101")
        expected = tmp_governance_root / "phases" / "phase-1" / "reviews" / "T101-review.md"
        assert path == expected

    def test_write_creates_file(self, writer, tmp_governance_root):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
            reviewer_host="codex",
        )
        result_path = writer.write(artifact)
        assert result_path.exists()
        assert result_path.name == "T101-review.md"

    def test_write_creates_directory(self, writer, tmp_governance_root):
        artifact = ReviewArtifact(
            task_id="T201",
            phase_id="phase-2",
            review_status="passed",
            decision="accepted",
        )
        result_path = writer.write(artifact)
        assert result_path.exists()
        assert result_path.parent.name == "reviews"

    def test_written_content_is_valid_markdown(self, writer):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
            summary="All acceptance tests passed",
            reviewer_host="codex",
        )
        result_path = writer.write(artifact)
        content = result_path.read_text(encoding="utf-8")
        assert "# Review Artifact: T101" in content
        assert "**Phase**: phase-1" in content
        assert "**Decision**: accepted" in content

    def test_write_with_blocker_findings(self, writer):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="failed",
            decision="rework_required",
            blocker_findings=[
                Finding(
                    severity="blocker",
                    category="security",
                    description="Hardcoded API key",
                    location="src/config.py:15",
                    suggested_fix="Use environment variable",
                ),
            ],
            reviewer_host="codex",
        )
        result_path = writer.write(artifact)
        content = result_path.read_text(encoding="utf-8")
        assert "## Blocker Findings" in content
        assert "Hardcoded API key" in content
        assert "Use environment variable" in content

    def test_write_with_acceptance_results(self, writer):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
            acceptance_results=[
                AcceptanceResult(
                    acceptance_id="A21",
                    passed=True,
                    evidence="tests/unit/test_review_artifact.py",
                ),
                AcceptanceResult(
                    acceptance_id="A22",
                    passed=False,
                    notes="Need integration test",
                ),
            ],
        )
        result_path = writer.write(artifact)
        content = result_path.read_text(encoding="utf-8")
        assert "## Acceptance Results" in content
        assert "A21" in content
        assert "PASS" in content
        assert "FAIL" in content

    def test_read_existing_artifact(self, writer):
        # 先写入
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
            reviewer_host="codex",
        )
        writer.write(artifact)

        # 再读取
        read_artifact = writer.read("phase-1", "T101")
        assert read_artifact is not None
        assert read_artifact.task_id == "T101"
        assert read_artifact.phase_id == "phase-1"
        assert read_artifact.decision == "accepted"

    def test_read_nonexistent_returns_none(self, writer):
        read_artifact = writer.read("phase-999", "T999")
        assert read_artifact is None

    def test_exists_true_after_write(self, writer):
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
        )
        writer.write(artifact)
        assert writer.exists("phase-1", "T101")

    def test_exists_false_before_write(self, writer):
        assert not writer.exists("phase-1", "T101")

    def test_overwrite_existing_artifact(self, writer):
        # 第一次写入
        artifact1 = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="in_review",
            decision="pending",
        )
        writer.write(artifact1)

        # 第二次写入（更新状态）
        artifact2 = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
        )
        writer.write(artifact2)

        # 读取验证
        read_artifact = writer.read("phase-1", "T101")
        assert read_artifact.decision == "accepted"


class TestA21Acceptance:
    """A21 验收测试：Review Artifact 落盘。"""

    def test_A21_review_artifact_written_to_correct_path(self, writer, tmp_governance_root):
        """A21 验收：文件路径可由 phase_id + task_id 稳定定位。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
            reviewer_host="codex",
        )
        result_path = writer.write(artifact)

        # 验收：路径符合规范
        expected_path = tmp_governance_root / "phases" / "phase-1" / "reviews" / "T101-review.md"
        assert result_path == expected_path
        assert result_path.exists()

    def test_A21_review_artifact_persisted_not_memory_only(self, writer, tmp_governance_root):
        """A21 验收：review artifact 落盘，不只在内存中保留。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
        )
        writer.write(artifact)

        # 验收：文件实际存在
        path = writer.get_review_path("phase-1", "T101")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "T101" in content
        assert "accepted" in content

    def test_A21_multiple_tasks_in_same_phase(self, writer):
        """A21 验收：同一 phase 多任务可独立定位。"""
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                review_status="passed",
                decision="accepted",
            )
            writer.write(artifact)

        # 每个任务都有独立文件
        assert writer.exists("phase-1", "T101")
        assert writer.exists("phase-1", "T102")
        assert writer.exists("phase-1", "T103")


class TestReviewStatusValues:
    """Review 状态枚举值测试。"""

    def test_valid_review_statuses(self):
        assert "pending" in VALID_REVIEW_STATUSES
        assert "in_review" in VALID_REVIEW_STATUSES
        assert "passed" in VALID_REVIEW_STATUSES
        assert "failed" in VALID_REVIEW_STATUSES

    def test_valid_decisions(self):
        assert "accepted" in VALID_DECISIONS
        assert "rework_required" in VALID_DECISIONS