"""T204: Gate Report Writer 测试。

验收标准 A25:
- phase 级 gate report 能统计 accepted / rework / blocker 状态
- 可给出 advance_allowed / reopen_required

关键约束:
- gate report 必须落盘到 phase 根目录
- advance_allowed 与 reopen_required 必须有明确来源
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from claudeflow.governance.gate_report import (
    GateReport,
    GateReportWriter,
)
from claudeflow.governance.review_artifact import (
    ReviewArtifact,
    ReviewArtifactWriter,
    Finding,
)
from claudeflow.governance.pipeline_state import PipelineStateStore


@pytest.fixture
def tmp_governance_root(tmp_path):
    """创建临时治理根目录。"""
    root = tmp_path / ".super-dev"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def gate_writer(tmp_governance_root):
    """创建 GateReportWriter。"""
    return GateReportWriter(tmp_governance_root)


@pytest.fixture
def pipeline_state_file(tmp_governance_root):
    """创建有效的 pipeline-state.json。"""
    state_path = tmp_governance_root / "pipeline-state.json"
    state_data = {
        "workflow_version": "v1",
        "project": "test-project",
        "current_phase": "phase-1",
        "current_stage": "implementation_review",
        "current_gate": "implementation_review",
        "gate_status": "open",
        "governor": {"host": "codex", "mode": "governor"},
        "advance_allowed": False,
        "reopen_required": False,
        "phases": {
            "phase-1": {
                "status": "implementation_review",
                "docs_ready": True,
                "tasks_ready": True,
                "quality_gate_passed": False,
                "completed_tasks": [],
                "pending_tasks": ["T101", "T102", "T103"],
            }
        },
        "tasks": {
            "T101": {
                "phase_id": "phase-1",
                "executor_type": "claude",
                "status": "submitted",
                "review_status": "pending",
            },
            "T102": {
                "phase_id": "phase-1",
                "executor_type": "claude",
                "status": "submitted",
                "review_status": "pending",
            },
            "T103": {
                "phase_id": "phase-1",
                "executor_type": "claude",
                "status": "submitted",
                "review_status": "pending",
            },
        },
        "timestamps": {"updated_at": "2026-01-01T00:00:00Z"},
    }
    state_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
    return state_path


@pytest.fixture
def review_writer(tmp_governance_root):
    """创建 ReviewArtifactWriter。"""
    return ReviewArtifactWriter(tmp_governance_root)


class TestGateReport:
    """GateReport 数据结构测试。"""

    def test_report_creation(self):
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101", "T102"],
            rework_required_tasks=[],
            blocker_count=0,
            advance_allowed=True,
            reopen_required=False,
            generated_at="2026-01-01T00:00:00Z",
        )
        assert report.phase_id == "phase-1"
        assert report.gate_status == "passed"
        assert len(report.accepted_tasks) == 2

    def test_report_to_markdown(self):
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101", "T102"],
            rework_required_tasks=["T103"],
            blocker_count=2,
            advance_allowed=False,
            reopen_required=True,
            generated_at="2026-01-01T00:00:00Z",
            summary="2 blockers found",
        )
        md = report.to_markdown()
        assert "# Gate Report: phase-1" in md
        assert "**Gate Status**: passed" in md
        assert "Accepted Tasks" in md
        assert "T101" in md
        assert "Rework Required Tasks" in md
        assert "T103" in md

    def test_report_to_dict(self):
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101"],
            blocker_count=0,
            advance_allowed=True,
            reopen_required=False,
        )
        d = report.to_dict()
        assert d["phase_id"] == "phase-1"
        assert d["advance_allowed"] is True

    def test_empty_lists_render_none(self):
        report = GateReport(
            phase_id="phase-1",
            gate_status="failed",
            accepted_tasks=[],
            rework_required_tasks=[],
        )
        md = report.to_markdown()
        assert "*None*" in md


class TestGateReportWriter:
    """GateReportWriter 主功能测试。"""

    def test_generate_from_empty_phase(self, gate_writer, tmp_governance_root):
        """空 phase 生成 report。"""
        report = gate_writer.generate("phase-999")
        assert report.phase_id == "phase-999"
        assert report.gate_status == "open"  # 无任务时为 open
        assert len(report.accepted_tasks) == 0

    def test_generate_with_accepted_reviews(
        self, gate_writer, review_writer, pipeline_state_file
    ):
        """全部 accepted 的 review 生成 passed gate。"""
        # 创建 accepted review
        artifact1 = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
        )
        artifact2 = ReviewArtifact(
            task_id="T102",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
        )
        review_writer.write(artifact1)
        review_writer.write(artifact2)

        report = gate_writer.generate("phase-1")
        assert "T101" in report.accepted_tasks
        assert "T102" in report.accepted_tasks
        assert len(report.rework_required_tasks) == 0

    def test_generate_with_rework_required(
        self, gate_writer, review_writer, pipeline_state_file
    ):
        """存在 rework_required 生成 reopen_required。"""
        artifact1 = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
        )
        artifact2 = ReviewArtifact(
            task_id="T102",
            phase_id="phase-1",
            review_status="failed",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="XSS"),
            ],
        )
        review_writer.write(artifact1)
        review_writer.write(artifact2)

        report = gate_writer.generate("phase-1")
        assert "T101" in report.accepted_tasks
        assert "T102" in report.rework_required_tasks
        assert report.reopen_required is True
        assert report.advance_allowed is False

    def test_generate_with_multiple_blockers(
        self, gate_writer, review_writer, pipeline_state_file
    ):
        """多个 blocker 统计正确。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="failed",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="XSS"),
                Finding(severity="blocker", category="logic", description="Null check"),
                Finding(severity="blocker", category="performance", description="N+1"),
            ],
        )
        review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        assert report.blocker_count == 3

    def test_write_creates_file(self, gate_writer):
        """写入 gate report 文件。"""
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101"],
            generated_at="2026-01-01T00:00:00Z",
        )
        path = gate_writer.write(report)
        assert path.exists()
        assert path.name == "gate-report.md"

    def test_write_content_valid_markdown(self, gate_writer):
        """写入的文件是有效 Markdown。"""
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101", "T102"],
            rework_required_tasks=["T103"],
            blocker_count=1,
            advance_allowed=False,
            reopen_required=True,
            generated_at="2026-01-01T00:00:00Z",
        )
        path = gate_writer.write(report)
        content = path.read_text(encoding="utf-8")

        assert "# Gate Report" in content
        assert "**Gate Status**: passed" in content
        assert "T101" in content
        assert "T103" in content

    def test_generate_and_write(self, gate_writer, pipeline_state_file):
        """生成并写入一体化。"""
        report, path = gate_writer.generate_and_write("phase-1")
        assert report is not None
        assert path is not None
        assert path.exists()

    def test_read_existing_report(self, gate_writer, tmp_governance_root):
        """读取已存在的 gate report。"""
        # 先写入
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101"],
            generated_at="2026-01-01T00:00:00Z",
        )
        gate_writer.write(report)

        # 再读取
        loaded = gate_writer.read("phase-1")
        assert loaded is not None
        assert loaded.phase_id == "phase-1"
        assert loaded.gate_status == "passed"

    def test_read_nonexistent_report(self, gate_writer):
        """读取不存在的 report 返回 None。"""
        loaded = gate_writer.read("phase-999")
        assert loaded is None

    def test_update_pipeline_state(self, gate_writer, pipeline_state_file):
        """更新 pipeline-state.json。"""
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101"],
            advance_allowed=True,
            reopen_required=False,
        )
        gate_writer.update_pipeline_state(report)

        # 验证更新
        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["phases"]["phase-1"]["advance_allowed"] is True
        assert state.raw["advance_allowed"] is True

    def test_update_pipeline_state_with_reopen(self, gate_writer, pipeline_state_file):
        """reopen_required 更新 pipeline-state。"""
        report = GateReport(
            phase_id="phase-1",
            gate_status="failed",
            rework_required_tasks=["T101"],
            blocker_count=1,
            advance_allowed=False,
            reopen_required=True,
        )
        gate_writer.update_pipeline_state(report)

        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["phases"]["phase-1"]["reopen_required"] is True
        assert state.raw["reopen_required"] is True


class TestA25Acceptance:
    """A25 验收测试：Gate Report 落盘。"""

    def test_A25_gate_report_statistics_accepted_rework(
        self, gate_writer, review_writer, pipeline_state_file
    ):
        """A25 验收：gate report 统计 accepted / rework / blocker 状态。"""
        # 创建不同状态的 review
        accepted = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="accepted",
            review_status="passed",
        )
        rework = ReviewArtifact(
            task_id="T102",
            phase_id="phase-1",
            decision="rework_required",
            review_status="failed",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="SQL injection"),
            ],
        )
        review_writer.write(accepted)
        review_writer.write(rework)

        report = gate_writer.generate("phase-1")
        assert "T101" in report.accepted_tasks
        assert "T102" in report.rework_required_tasks
        assert report.blocker_count >= 1

    def test_A25_advance_allowed_when_all_accepted(
        self, gate_writer, review_writer, pipeline_state_file
    ):
        """A25 验收：全部通过时 advance_allowed = true。"""
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="accepted",
                review_status="passed",
            )
            review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        assert report.advance_allowed is True
        assert report.reopen_required is False

    def test_A25_reopen_required_when_blockers(
        self, gate_writer, review_writer, pipeline_state_file
    ):
        """A25 验收：存在 blocker 时 reopen_required = true。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            review_status="failed",
            blocker_findings=[
                Finding(severity="blocker", category="logic", description="Bug"),
            ],
        )
        review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        assert report.reopen_required is True
        assert report.advance_allowed is False

    def test_A25_gate_report_written_to_phase_root(
        self, gate_writer, tmp_governance_root
    ):
        """A25 验收：gate report 落盘到 phase 根目录。"""
        report, path = gate_writer.generate_and_write("phase-1")
        assert path is not None

        # 验证路径在 phase 根目录
        assert path.parent.name == "phase-1"
        assert path.parent.parent.name == "phases"
        assert path.name == "gate-report.md"

    def test_A25_advance_reopen_have_clear_source(
        self, gate_writer, review_writer, pipeline_state_file
    ):
        """A25 验收：advance_allowed 与 reopen_required 有明确来源。"""
        accepted = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="accepted",
        )
        rework = ReviewArtifact(
            task_id="T102",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="Issue"),
            ],
        )
        review_writer.write(accepted)
        review_writer.write(rework)

        report = gate_writer.generate("phase-1")

        # 来源明确：基于 accepted_tasks 和 rework_required_tasks
        assert report.advance_allowed == (len(report.rework_required_tasks) == 0)
        assert report.reopen_required == (len(report.rework_required_tasks) > 0)


class TestGateReportEdgeCases:
    """Gate Report 边界场景测试。"""

    def test_partial_pass(self, gate_writer, review_writer, pipeline_state_file):
        """部分通过状态。"""
        accepted = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="accepted",
        )
        pending_artifact = None  # T102 没有 review

        review_writer.write(accepted)

        report = gate_writer.generate("phase-1")
        # 有 accepted 但不全部，gate_status 应为 partial
        assert "T101" in report.accepted_tasks

    def test_all_blocked(self, gate_writer, review_writer, pipeline_state_file):
        """全部 blocker 状态。"""
        for task_id in ["T101", "T102"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="rework_required",
                blocker_findings=[
                    Finding(severity="blocker", category="logic", description="Bug"),
                ],
            )
            review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        assert len(report.accepted_tasks) == 0
        assert len(report.rework_required_tasks) == 2
        assert report.gate_status == "failed"

    def test_report_survives_reload(self, gate_writer, tmp_governance_root):
        """report 数据在重新加载后保持。"""
        report = GateReport(
            phase_id="phase-1",
            gate_status="passed",
            accepted_tasks=["T101", "T102"],
            advance_allowed=True,
            generated_at="2026-01-01T00:00:00Z",
        )
        gate_writer.write(report)

        # 重新加载
        loaded = gate_writer.read("phase-1")
        assert loaded is not None
        assert "T101" in loaded.accepted_tasks
        assert "T102" in loaded.accepted_tasks


class TestIntegrationWithPipelineState:
    """Gate Report 与 Pipeline State 集成测试。"""

    def test_full_workflow(
        self, gate_writer, review_writer, pipeline_state_file, tmp_governance_root
    ):
        """完整工作流：review -> gate report -> pipeline update。"""
        # 1. 创建 reviews - 所有 3 个任务都通过
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="accepted",
                review_status="passed",
            )
            review_writer.write(artifact)

        # 2. 生成 gate report
        report, path = gate_writer.generate_and_write("phase-1")
        assert report.advance_allowed is True

        # 3. 更新 pipeline state
        gate_writer.update_pipeline_state(report)

        # 4. 验证最终状态
        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["advance_allowed"] is True
        assert state.raw["phases"]["phase-1"]["quality_gate_passed"] is True