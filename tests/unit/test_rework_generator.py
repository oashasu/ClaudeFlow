"""T203: Rework Task Generator 测试。

验收标准 A23:
- review 判定 rework_required 后生成返工任务包
- 返工任务包继承原任务关键约束

关键约束:
- 返工任务必须继承原 allowed_write_paths 与 acceptance_refs
- 不得发明新 schema 替代 task package

返工任务包路径: .super-dev/phases/<phase-id>/tasks/<original-id>-R<n>.yaml
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path

import pytest

from claudeflow.governance.rework_generator import (
    ReworkContext,
    ReworkTaskGenerator,
    ReworkTaskPackage,
)
from claudeflow.governance.review_artifact import (
    Finding,
    ReviewArtifact,
)
from claudeflow.governance.task_loader import TaskPackage


@pytest.fixture
def tmp_governance_root(tmp_path):
    """创建临时治理根目录。"""
    root = tmp_path / ".super-dev"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def generator(tmp_governance_root):
    """创建 ReworkTaskGenerator。"""
    return ReworkTaskGenerator(tmp_governance_root)


@pytest.fixture
def original_task_yaml(tmp_governance_root):
    """创建原始任务包。"""
    tasks_dir = tmp_governance_root / "phases" / "phase-1" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    task_data = {
        "id": "T101",
        "phase_id": "phase-1",
        "title": "Implement feature X",
        "executor_type": "claude",
        "reviewer_type": "governor",
        "priority": "high",
        "inputs": ["../spec.md", "../architecture.md"],
        "constraints": ["Must pass all tests", "No security issues"],
        "allowed_write_paths": ["src/**", "tests/**"],
        "acceptance_refs": ["A21", "A22"],
        "outputs": ["changed_files", "test_evidence", "summary"],
        "done_definition": ["tests_pass", "review_ready"],
        "rework_policy": {"max_rounds": 2, "inherit_previous_findings": True},
        "gate_on_complete": "review_required",
    }

    task_path = tasks_dir / "T101.yaml"
    task_path.write_text(yaml.dump(task_data, allow_unicode=True), encoding="utf-8")
    return task_path


@pytest.fixture
def review_artifact_with_blockers(tmp_governance_root, original_task_yaml):
    """创建带 blocker 的 review artifact。"""
    reviews_dir = tmp_governance_root / "phases" / "phase-1" / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)

    artifact = ReviewArtifact(
        task_id="T101",
        phase_id="phase-1",
        review_status="failed",
        decision="rework_required",
        blocker_findings=[
            Finding(
                severity="blocker",
                category="security",
                description="Hardcoded API key detected",
                location="src/config.py:15",
                suggested_fix="Use environment variable",
            ),
            Finding(
                severity="blocker",
                category="logic",
                description="Missing null check before dereference",
                location="src/main.py:42",
            ),
        ],
        non_blocker_findings=[
            Finding(
                severity="non_blocker",
                category="style",
                description="Variable naming could be clearer",
            ),
        ],
        summary="Review failed with 2 blockers",
        reviewer_host="codex",
    )

    review_path = reviews_dir / "T101-review.md"
    review_path.write_text(artifact.to_markdown(), encoding="utf-8")
    return artifact


class TestReworkContext:
    """ReworkContext 数据结构测试。"""

    def test_context_creation(self):
        ctx = ReworkContext(
            original_task_id="T101",
            findings_ref="../reviews/T101-review.md",
            rework_round=1,
            blocker_count=2,
            summary="Fix security issues",
        )
        assert ctx.original_task_id == "T101"
        assert ctx.rework_round == 1

    def test_context_to_dict(self):
        ctx = ReworkContext(
            original_task_id="T101",
            findings_ref="../reviews/T101-review.md",
            rework_round=1,
            blocker_count=2,
        )
        d = ctx.to_dict()
        assert d["original_task_id"] == "T101"
        assert d["rework_round"] == 1
        assert d["blocker_count"] == 2


class TestReworkTaskPackage:
    """ReworkTaskPackage 数据结构测试。"""

    def test_rework_package_creation(self):
        ctx = ReworkContext(
            original_task_id="T101",
            findings_ref="../reviews/T101-review.md",
            rework_round=1,
            blocker_count=2,
        )
        pkg = ReworkTaskPackage(
            id="T101-R1",
            phase_id="phase-1",
            title="[Rework R1] Fix 2 blockers from review",
            executor_type="claude",
            reviewer_type="governor",
            inputs=["../spec.md", "../reviews/T101-review.md"],
            constraints=["Fix blocker: Hardcoded API key"],
            allowed_write_paths=["src/**", "tests/**"],
            acceptance_refs=["A21", "A22"],
            done_definition=["tests_pass", "review_ready"],
            gate_on_complete="review_required",
            rework_context=ctx,
            generated_at="2026-01-01T00:00:00Z",
        )
        assert pkg.id == "T101-R1"
        assert pkg.executor_type == "claude"

    def test_rework_package_to_yaml_dict(self):
        ctx = ReworkContext(
            original_task_id="T101",
            findings_ref="../reviews/T101-review.md",
            rework_round=1,
            blocker_count=2,
        )
        pkg = ReworkTaskPackage(
            id="T101-R1",
            phase_id="phase-1",
            title="Rework task",
            executor_type="claude",
            reviewer_type="governor",
            inputs=["../spec.md"],
            constraints=["Fix blocker"],
            allowed_write_paths=["src/**"],
            acceptance_refs=["A21"],
            done_definition=["tests_pass"],
            gate_on_complete="review_required",
            rework_context=ctx,
            generated_at="2026-01-01T00:00:00Z",
        )
        d = pkg.to_yaml_dict()
        assert "rework_context" in d
        assert d["id"] == "T101-R1"


class TestReworkTaskGenerator:
    """ReworkTaskGenerator 主功能测试。"""

    def test_generate_from_review_artifact(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """从 review artifact 生成返工任务。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert rework_pkg.id == "T101-R1"
        assert rework_pkg.executor_type == "claude"
        assert rework_pkg.rework_context.original_task_id == "T101"
        assert rework_pkg.rework_context.rework_round == 1
        assert rework_pkg.rework_context.blocker_count == 2

    def test_generate_inherits_allowed_write_paths(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """A23 验收：返工任务继承 allowed_write_paths。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert "src/**" in rework_pkg.allowed_write_paths
        assert "tests/**" in rework_pkg.allowed_write_paths

    def test_generate_inherits_acceptance_refs(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """A23 验收：返工任务继承 acceptance_refs。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert "A21" in rework_pkg.acceptance_refs
        assert "A22" in rework_pkg.acceptance_refs

    def test_generate_inherits_executor_type(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """A23 验收：返工任务继承 executor_type。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert rework_pkg.executor_type == "claude"

    def test_generate_inherits_gate_on_complete(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """A23 验收：返工任务继承 gate_on_complete。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert rework_pkg.gate_on_complete == "review_required"

    def test_generate_adds_findings_ref_to_inputs(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """返工任务 inputs 包含 review artifact 引用。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert "../reviews/T101-review.md" in rework_pkg.inputs

    def test_generate_includes_blocker_constraints(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """返工任务 constraints 包含 blocker 信息。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        # 原约束 + blocker 约束
        assert len(rework_pkg.constraints) >= len(review_artifact_with_blockers.blocker_findings)

    def test_generate_returns_none_for_accepted_decision(
        self, generator, original_task_yaml
    ):
        """accepted decision 不生成返工任务。"""
        artifact = ReviewArtifact(
            task_id="T101",
            phase_id="phase-1",
            review_status="passed",
            decision="accepted",
        )

        rework_pkg = generator.generate(
            review_artifact=artifact,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is None

    def test_generate_returns_none_for_no_original_task(self, generator):
        """无原始任务包时无法生成返工任务。"""
        artifact = ReviewArtifact(
            task_id="T999",
            phase_id="phase-1",
            review_status="failed",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="logic", description="Bug"),
            ],
        )

        rework_pkg = generator.generate(
            review_artifact=artifact,
            original_task_id="T999",
            phase_id="phase-1",
        )

        assert rework_pkg is None

    def test_write_creates_yaml_file(
        self, generator, review_artifact_with_blockers, original_task_yaml, tmp_governance_root
    ):
        """写入返工任务 YAML 文件。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )
        assert rework_pkg is not None

        result_path = generator.write(rework_pkg)
        assert result_path.exists()
        assert result_path.name == "T101-R1.yaml"

    def test_write_content_valid_yaml(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """写入的文件是有效 YAML。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )
        assert rework_pkg is not None

        result_path = generator.write(rework_pkg)
        content = result_path.read_text(encoding="utf-8")

        loaded = yaml.safe_load(content)
        assert loaded["id"] == "T101-R1"
        assert "rework_context" in loaded

    def test_generate_and_write(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """生成并写入一体化。"""
        rework_pkg, path = generator.generate_and_write(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert path is not None
        assert path.exists()

    def test_get_rework_tasks(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """获取所有返工任务。"""
        # 生成第一轮返工
        generator.generate_and_write(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        rework_tasks = generator.get_rework_tasks("phase-1", "T101")
        assert len(rework_tasks) == 1
        assert rework_tasks[0].id == "T101-R1"

    def test_has_rework_tasks(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """检查是否有返工任务。"""
        assert not generator.has_rework_tasks("phase-1", "T101")

        generator.generate_and_write(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert generator.has_rework_tasks("phase-1", "T101")


class TestA23Acceptance:
    """A23 验收测试：返工任务自动生成。"""

    def test_A23_rework_task_generated_after_rework_required(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """A23 验收：review 判定 rework_required 后生成返工任务包。"""
        rework_pkg, path = generator.generate_and_write(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert path is not None
        assert path.name == "T101-R1.yaml"

    def test_A23_rework_task_inherits_constraints(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """A23 验收：返工任务包继承原任务关键约束。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        # 继承检查
        assert rework_pkg.phase_id == "phase-1"
        assert rework_pkg.executor_type == "claude"
        assert rework_pkg.gate_on_complete == "review_required"
        assert "src/**" in rework_pkg.allowed_write_paths
        assert "A21" in rework_pkg.acceptance_refs

    def test_A23_rework_task_has_rework_context(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """A23 验收：返工任务包含 rework_context。"""
        rework_pkg = generator.generate(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg.rework_context.original_task_id == "T101"
        assert rework_pkg.rework_context.rework_round == 1
        assert rework_pkg.rework_context.findings_ref.endswith("review.md")


class TestMultipleReworkRounds:
    """多轮返工测试。"""

    def test_second_round_rework(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """第二轮返工任务。"""
        # 第一轮
        generator.generate_and_write(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        # 模拟第二轮 review
        second_review = ReviewArtifact(
            task_id="T101-R1",
            phase_id="phase-1",
            review_status="failed",
            decision="rework_required",
            blocker_findings=[
                Finding(severity="blocker", category="logic", description="Still broken"),
            ],
        )

        # 第二轮返工
        rework_pkg, path = generator.generate_and_write(
            review_artifact=second_review,
            original_task_id="T101",
            phase_id="phase-1",
        )

        assert rework_pkg is not None
        assert rework_pkg.id == "T101-R2"
        assert rework_pkg.rework_context.rework_round == 2

    def test_max_rounds_limit(
        self, generator, review_artifact_with_blockers, original_task_yaml
    ):
        """超过最大轮次不生成返工任务。"""
        # 第一轮
        generator.generate_and_write(
            review_artifact=review_artifact_with_blockers,
            original_task_id="T101",
            phase_id="phase-1",
        )

        # 第二轮
        second_review = ReviewArtifact(
            task_id="T101-R1",
            phase_id="phase-1",
            review_status="failed",
            decision="rework_required",
            blocker_findings=[Finding(severity="blocker", category="logic", description="Bug")],
        )
        generator.generate_and_write(
            review_artifact=second_review,
            original_task_id="T101",
            phase_id="phase-1",
        )

        # 第三轮（超过限制）
        third_review = ReviewArtifact(
            task_id="T101-R2",
            phase_id="phase-1",
            review_status="failed",
            decision="rework_required",
            blocker_findings=[Finding(severity="blocker", category="logic", description="Bug")],
        )

        rework_pkg = generator.generate(
            review_artifact=third_review,
            original_task_id="T101",
            phase_id="phase-1",
        )

        # 第三轮不应生成
        assert rework_pkg is None