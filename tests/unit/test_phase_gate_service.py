"""T205: Phase Gate Service 测试。

验收标准 A24:
- review 判定 accepted 后原任务进入 accepted
- 不生成多余 rework task

验收标准 A26:
- 全部通过时 phase 可推进
- 存在 blocker 或返工时 phase 不得推进，并可 reopen

关键约束:
- 不得在无 gate report 的情况下推进 phase
- 不得让 review fail 仍然保持 advance_allowed=true
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path

import pytest

from claudeflow.governance.phase_gate_service import (
    PhaseGateService,
    PhaseGateResult,
)
from claudeflow.governance.gate_report import GateReport, GateReportWriter
from claudeflow.governance.review_artifact import (
    ReviewArtifact,
    ReviewArtifactWriter,
    Finding,
)
from claudeflow.governance.pipeline_state import PipelineStateStore
from claudeflow.governance.rework_generator import ReworkTaskGenerator


@pytest.fixture
def governance_setup(tmp_path):
    """创建完整的治理环境，包括目录和 pipeline-state.json。"""
    root = tmp_path / ".super-dev"
    root.mkdir(parents=True, exist_ok=True)

    state_path = root / "pipeline-state.json"
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

    # Create tasks directory and T101.yaml
    tasks_dir = root / "phases" / "phase-1" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    task_data = {
        "id": "T101",
        "phase_id": "phase-1",
        "title": "Implement feature X",
        "executor_type": "claude",
        "reviewer_type": "governor",
        "priority": "high",
        "inputs": ["../spec.md"],
        "constraints": ["Must pass all tests"],
        "allowed_write_paths": ["src/**"],
        "acceptance_refs": ["A21"],
        "outputs": ["changed_files"],
        "done_definition": ["tests_pass"],
        "rework_policy": {"max_rounds": 2},
        "gate_on_complete": "review_required",
    }

    task_path = tasks_dir / "T101.yaml"
    task_path.write_text(yaml.dump(task_data, allow_unicode=True), encoding="utf-8")

    return {
        "root": root,
        "state_path": state_path,
        "task_path": task_path,
    }


@pytest.fixture
def gate_service(governance_setup):
    """创建 PhaseGateService - 确保 pipeline_state_file 已创建。"""
    return PhaseGateService(governance_setup["root"])


@pytest.fixture
def pipeline_state_file(governance_setup):
    """返回 pipeline-state.json 路径。"""
    return governance_setup["state_path"]


@pytest.fixture
def original_task_yaml(governance_setup):
    """返回原始任务包路径。"""
    return governance_setup["task_path"]


@pytest.fixture
def review_writer(governance_setup):
    """创建 ReviewArtifactWriter。"""
    return ReviewArtifactWriter(governance_setup["root"])


@pytest.fixture
def gate_writer(governance_setup):
    """创建 GateReportWriter。"""
    return GateReportWriter(governance_setup["root"])


class TestPhaseGateResult:
    """PhaseGateResult 数据结构测试。"""

    def test_result_creation(self):
        result = PhaseGateResult(
            phase_id="phase-1",
            action="advance",
            success=True,
            reason="All tasks accepted",
        )
        assert result.phase_id == "phase-1"
        assert result.action == "advance"
        assert result.success is True

    def test_result_to_dict(self):
        result = PhaseGateResult(
            phase_id="phase-1",
            action="reopen",
            success=True,
            reason="Blockers found",
            updated_tasks=["T101"],
        )
        d = result.to_dict()
        assert d["phase_id"] == "phase-1"
        assert d["action"] == "reopen"
        assert "T101" in d["updated_tasks"]


class TestPhaseGateService:
    """PhaseGateService 主功能测试。"""

    def test_update_task_status_accepted(self, gate_service, pipeline_state_file):
        """accepted 路径更新任务状态。"""
        result = gate_service.update_task_status("phase-1", "T101", "accepted")
        assert result is not None
        assert result.action == "task_accepted"
        assert result.success is True

        # 验证 pipeline-state
        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["tasks"]["T101"]["status"] == "accepted"
        assert state.raw["tasks"]["T101"]["review_status"] == "accepted"

    def test_update_task_status_rework_required(
        self, gate_service, pipeline_state_file
    ):
        """rework_required 路径更新任务状态。"""
        result = gate_service.update_task_status("phase-1", "T101", "rework_required")
        assert result is not None
        assert result.action == "task_rework_required"
        assert result.success is True

        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["tasks"]["T101"]["status"] == "rework_required"

    def test_update_task_status_invalid_decision(self, gate_service):
        """无效 decision 返回 None。"""
        result = gate_service.update_task_status("phase-1", "T101", "invalid")
        assert result is None

    def test_update_task_moves_to_completed(
        self, gate_service, pipeline_state_file
    ):
        """accepted 任务移入 completed_tasks。"""
        gate_service.update_task_status("phase-1", "T101", "accepted")

        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert "T101" in state.raw["phases"]["phase-1"]["completed_tasks"]
        assert "T101" not in state.raw["phases"]["phase-1"]["pending_tasks"]

    def test_can_advance_phase_no_gate_report(self, gate_service):
        """无 gate report 不能推进。"""
        can_advance, reason = gate_service.can_advance_phase("phase-999")
        assert can_advance is False
        assert "No gate report" in reason

    def test_can_advance_phase_with_blockers(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """有 blockers 不能推进。"""
        # 创建 failed review
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="XSS"),
            ],
        )
        review_writer.write(artifact)

        # 生成 gate report
        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        can_advance, reason = gate_service.can_advance_phase("phase-1")
        assert can_advance is False

    def test_can_advance_phase_all_accepted(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """全部 accepted 可以推进。"""
        # 创建所有 accepted reviews
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="accepted",
            )
            review_writer.write(artifact)

        # 生成 gate report
        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        can_advance, reason = gate_service.can_advance_phase("phase-1")
        assert can_advance is True

    def test_advance_phase_without_gate_report(self, gate_service):
        """无 gate report 推进失败。"""
        result = gate_service.advance_phase("phase-999")
        assert result.success is False
        assert result.action == "blocked"

    def test_advance_phase_with_blockers(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """有 blockers 推进失败。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="logic", description="Bug"),
            ],
        )
        review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        result = gate_service.advance_phase("phase-1")
        assert result.success is False
        assert result.action == "blocked"

    def test_advance_phase_success(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """全部通过成功推进。"""
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="accepted",
            )
            review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        result = gate_service.advance_phase("phase-1")
        assert result.success is True
        assert result.action == "advance"

        # 验证 pipeline-state
        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["phases"]["phase-1"]["status"] == "accepted"

    def test_reopen_phase_without_blockers(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """无 blockers 不能 reopen。"""
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="accepted",
            )
            review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        result = gate_service.reopen_phase("phase-1")
        assert result.success is False
        assert result.action == "blocked"

    def test_reopen_phase_with_blockers(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """有 blockers 成功 reopen。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="Issue"),
            ],
        )
        review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        result = gate_service.reopen_phase("phase-1")
        assert result.success is True
        assert result.action == "reopen"

        # 验证 pipeline-state
        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["phases"]["phase-1"]["status"] == "reopened"


class TestA24Acceptance:
    """A24 验收测试：Accepted 路径。"""

    def test_A24_accepted_task_enters_accepted_status(
        self, gate_service, pipeline_state_file
    ):
        """A24 验收：review 判定 accepted 后原任务进入 accepted。"""
        result = gate_service.update_task_status("phase-1", "T101", "accepted")
        assert result is not None

        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["tasks"]["T101"]["status"] == "accepted"
        assert state.raw["tasks"]["T101"]["review_status"] == "accepted"

    def test_A24_no_extra_rework_task_for_accepted(
        self, gate_service, review_writer, original_task_yaml
    ):
        """A24 验收：accepted 不生成返工任务。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="accepted",
        )

        result = gate_service.process_review_decision(
            phase_id="phase-1",
            task_id="T101",
            review_artifact=artifact,
        )

        # 检查没有返工任务文件
        rework_generator = ReworkTaskGenerator(original_task_yaml.parent.parent.parent)
        assert not rework_generator.has_rework_tasks("phase-1", "T101")


class TestA26Acceptance:
    """A26 验收测试：Phase Reopen / Advance。"""

    def test_A26_phase_advance_when_all_pass(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """A26 验收：全部通过时 phase 可推进。"""
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="accepted",
            )
            review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        result = gate_service.advance_phase("phase-1")
        assert result.success is True
        assert "accepted" in result.reason.lower() or "advance" in result.action

    def test_A26_phase_reopen_with_blockers(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """A26 验收：存在 blocker 或返工时 phase 不得推进，并可 reopen。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="logic", description="Bug"),
            ],
        )
        review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        # 不能推进
        can_advance, _ = gate_service.can_advance_phase("phase-1")
        assert can_advance is False

        # 可以 reopen
        result = gate_service.reopen_phase("phase-1")
        assert result.success is True
        assert result.action == "reopen"

    def test_A26_no_gate_report_means_no_advance(self, gate_service):
        """A26 验收：无 gate report 不能推进。"""
        can_advance, reason = gate_service.can_advance_phase("phase-999")
        assert can_advance is False
        assert "No gate report" in reason

    def test_A26_review_fail_keeps_advance_false(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """A26 验收：review fail 时 advance_allowed=false。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="XSS"),
            ],
        )
        review_writer.write(artifact)

        report = gate_writer.generate("phase-1")
        gate_writer.write(report)

        # 验证 advance_allowed = false
        assert report.advance_allowed is False


class TestProcessReviewDecision:
    """process_review_decision 完整流程测试。"""

    def test_process_accepted_review(
        self, gate_service, review_writer, original_task_yaml, pipeline_state_file
    ):
        """处理 accepted review 完整流程。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="accepted",
        )
        review_writer.write(artifact)

        result = gate_service.process_review_decision(
            phase_id="phase-1",
            task_id="T101",
            review_artifact=artifact,
        )

        assert result.success is True
        assert "T101" in result.updated_tasks

    def test_process_rework_review(
        self, gate_service, review_writer, original_task_yaml, pipeline_state_file
    ):
        """处理 rework_required review 完整流程。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="logic", description="Bug"),
            ],
        )
        review_writer.write(artifact)

        result = gate_service.process_review_decision(
            phase_id="phase-1",
            task_id="T101",
            review_artifact=artifact,
        )

        assert result.success is True
        # 应生成返工任务
        rework_generator = ReworkTaskGenerator(gate_service.governance_root)
        assert rework_generator.has_rework_tasks("phase-1", "T101")


class TestGetPhaseStatus:
    """get_phase_status 测试。"""

    def test_get_phase_status(self, gate_service, pipeline_state_file):
        """获取 phase 状态摘要。"""
        status = gate_service.get_phase_status("phase-1")
        assert status["phase_id"] == "phase-1"
        assert status["status"] == "implementation_review"
        assert status["pending_tasks"] == 3
        assert status["completed_tasks"] == 0


class TestIntegration:
    """集成测试。"""

    def test_full_accepted_flow(
        self, gate_service, gate_writer, review_writer, pipeline_state_file
    ):
        """完整 accepted 流程：review -> gate -> advance。"""
        # 1. 所有任务 accepted
        for task_id in ["T101", "T102", "T103"]:
            artifact = ReviewArtifact(
                task_id=task_id,
                phase_id="phase-1",
                decision="accepted",
            )
            review_writer.write(artifact)
            gate_service.update_task_status("phase-1", task_id, "accepted")

        # 2. 生成 gate report
        report = gate_writer.generate("phase-1")
        gate_writer.write(report)
        assert report.advance_allowed is True

        # 3. 推进 phase
        result = gate_service.advance_phase("phase-1")
        assert result.success is True

        # 4. 验证最终状态
        store = PipelineStateStore(pipeline_state_file)
        state, _ = store.load()
        assert state.raw["phases"]["phase-1"]["status"] == "accepted"

    def test_full_rework_flow(
        self,
        gate_service,
        gate_writer,
        review_writer,
        pipeline_state_file,
        original_task_yaml,
    ):
        """完整 rework 流程：review -> gate -> reopen -> rework task。"""
        # 1. 一个任务 rework_required
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="security", description="XSS"),
            ],
        )
        review_writer.write(artifact)

        result = gate_service.process_review_decision(
            phase_id="phase-1",
            task_id="T101",
            review_artifact=artifact,
        )

        # 2. 验证 phase reopen
        assert result.action == "reopen" or result.action == "pending"

        # 3. 验证返工任务生成
        rework_generator = ReworkTaskGenerator(gate_service.governance_root)
        assert rework_generator.has_rework_tasks("phase-1", "T101")