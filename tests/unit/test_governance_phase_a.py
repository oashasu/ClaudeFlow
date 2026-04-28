"""Phase A 验收测试 — 覆盖 A01-A08 全部场景。

对应文档:
- 05_PhaseA_验收标准.md
- 09_Governor编排对象Schema设计.md

Schema 关键:
- current_phase 是 phase ID（如 "phase-1"），不是 phase status
- phase status 放在 phases.<id>.status 中
- tasks 是按任务 ID 索引的对象，不是数组
- executor_type: claude|codex|future
- reviewer_type: governor|external-reviewer
- done_definition: 数组
- gate_on_complete: review_required|acceptance_required
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import pytest
import yaml

from claudeflow.governance.pipeline_state import (
    PipelineState,
    PipelineStateError,
    PipelineStateStore,
    VALID_PHASE_STATUSES,
    VALID_GATE_STATUSES,
)
from claudeflow.governance.poller import ChangeRecord, GovernancePoller
from claudeflow.governance.state_machine import (
    GateStatus,
    GovernancePhase,
    GovernanceStateMachine,
    IllegalTransitionError,
)
from claudeflow.governance.task_loader import (
    TaskPackage,
    TaskPackageError,
    TaskPackageLoader,
)
from claudeflow.governance.workspace import (
    GovernanceWorkspace,
    WorkspacePaths,
)


@pytest.fixture
def tmp_project(tmp_path):
    """创建临时项目目录。"""
    return tmp_path


@pytest.fixture
def workspace(tmp_project):
    return GovernanceWorkspace(tmp_project)


def _valid_pipeline_state():
    return {
        "workflow_version": "v1",
        "project": "test-project",
        "current_phase": "phase-1",
        "current_stage": "research",
        "current_gate": "docs_confirm",
        "gate_status": "open",
        "governor": {"host": "codex", "mode": "governor"},
        "advance_allowed": False,
        "reopen_required": False,
        "phases": {
            "phase-1": {
                "status": "drafting",
                "docs_ready": False,
                "tasks_ready": False,
                "quality_gate_passed": False,
            },
        },
        "tasks": {},
        "timestamps": {"updated_at": "2026-04-26T00:00:00+00:00"},
    }


def _valid_task_yaml():
    return {
        "id": "T001",
        "phase_id": "phase-1",
        "title": "实现 GovernanceWorkspace",
        "executor_type": "claude",
        "reviewer_type": "governor",
        "inputs": ["设计文档"],
        "constraints": ["幂等"],
        "allowed_write_paths": ["src/governance/"],
        "acceptance_refs": ["A01"],
        "done_definition": ["build_pass", "acceptance_ready"],
        "gate_on_complete": "review_required",
    }


# ============================================================
# A01: .super-dev/ 初始化
# ============================================================


class TestA01WorkspaceInit:
    """A01: .super-dev/ 初始化 — 目录和最小文件创建成功，重复执行不破坏已有内容。"""

    def test_init_creates_structure(self, workspace, tmp_project):
        paths = workspace.initialize()
        assert paths.root.is_dir()
        assert paths.workflow_md.exists()
        assert paths.pipeline_state.exists()
        assert paths.roles_yaml.exists()
        assert paths.phases_dir.is_dir()

    def test_init_creates_valid_default_state(self, workspace):
        paths = workspace.initialize()
        store = PipelineStateStore(paths.pipeline_state)
        state, errors = store.load()
        assert not errors, f"默认状态校验失败: {[e.reason for e in errors]}"
        assert state.current_phase == "phase-1"
        assert state.get_phase_status("phase-1") == "drafting"

    def test_init_idempotent(self, workspace):
        paths1 = workspace.initialize()
        content_before = paths1.workflow_md.read_text()
        state_before = paths1.pipeline_state.read_text()

        paths2 = workspace.initialize()
        assert paths2.workflow_md.read_text() == content_before
        assert paths2.pipeline_state.read_text() == state_before

    def test_init_preserves_modified_files(self, workspace):
        paths = workspace.initialize()
        custom = "# Custom workflow content"
        paths.workflow_md.write_text(custom, encoding="utf-8")

        workspace.initialize()
        assert paths.workflow_md.read_text() == custom

    def test_is_initialized(self, workspace):
        assert not workspace.is_initialized()
        workspace.initialize()
        assert workspace.is_initialized()


# ============================================================
# A02: pipeline-state.json 合法读写
# ============================================================


class TestA02PipelineStateReadWrite:
    """A02: 加载合法样例，修改 current_gate 后写回，能重新读取到新值，updated_at 被刷新。"""

    def test_load_valid_state(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        store = PipelineStateStore(state_file)
        state, errors = store.load()
        assert not errors
        assert state.current_phase == "phase-1"
        assert state.gate_status == "open"
        assert state.get_phase_status("phase-1") == "drafting"

    def test_save_and_reload(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        store = PipelineStateStore(state_file)
        state, _ = store.load()
        state.current_gate = "implementation_review"
        state.gate_status = "passed"
        store.save(state)

        reloaded, errors = store.load()
        assert not errors
        assert reloaded.current_gate == "implementation_review"
        assert reloaded.gate_status == "passed"

    def test_updated_at_refreshed_on_save(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        store = PipelineStateStore(state_file)
        state, _ = store.load()
        old_updated = state.updated_at
        time.sleep(0.01)
        store.save(state)

        reloaded, _ = store.load()
        assert reloaded.updated_at != old_updated

    def test_update_and_save_atomic(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        store = PipelineStateStore(state_file)
        new_state, errors = store.update_and_save({
            "phases": {
                "phase-1": {
                    "status": "docs_confirm",
                    "docs_ready": True,
                    "tasks_ready": False,
                    "quality_gate_passed": False,
                },
            },
        })
        assert not errors
        assert new_state.get_phase_status("phase-1") == "docs_confirm"


# ============================================================
# A03: pipeline-state.json 非法输入
# ============================================================


class TestA03PipelineStateInvalid:
    """A03: 删除必填字段或伪造非法枚举 → 返回结构化错误，不污染旧状态。"""

    def test_missing_required_field(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        del payload["phases"]
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert len(errors) >= 1
        assert any(e.field_name == "phases" for e in errors)

    def test_invalid_phase_status(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["phases"]["phase-1"]["status"] = "nonexistent_status"
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(
            e.field_name == "phases.phase-1.status" and e.error_type == "enum_error"
            for e in errors
        )

    def test_invalid_gate_enum(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["gate_status"] = "maybe"
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(e.field_name == "gate_status" and e.error_type == "enum_error" for e in errors)

    def test_invalid_current_gate_enum(self, tmp_project):
        """current_gate 枚举值非法时应报错。"""
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["current_gate"] = "invalid_gate"
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(e.field_name == "current_gate" and e.error_type == "enum_error" for e in errors)

    def test_tasks_as_array_rejected(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["tasks"] = []
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(e.field_name == "tasks" for e in errors)

    def test_current_phase_not_in_phases(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["current_phase"] = "phase-999"
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(
            e.field_name == "current_phase" and e.error_type == "reference_error"
            for e in errors
        )

    def test_invalid_json(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        state_file.write_text("{bad json}", encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert errors[0].error_type == "json_parse_error"

    def test_file_not_found(self, tmp_project):
        store = PipelineStateStore(tmp_project / "nonexistent.json")
        _, errors = store.load()
        assert errors[0].error_type == "file_not_found"

    def test_bad_update_does_not_pollute_old_state(self, tmp_project):
        state_file = tmp_project / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.update_and_save({"current_phase": "phase-999"})
        assert errors

        reloaded, reloaded_errors = store.load()
        assert not reloaded_errors
        assert reloaded.current_phase == "phase-1"

    def test_missing_governor_host(self, tmp_project):
        """governor.host 必填字段缺失时应报错。"""
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["governor"] = {"mode": "governor"}  # 缺少 host
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(e.field_name == "governor.host" and e.error_type == "missing_field" for e in errors)

    def test_missing_timestamps_updated_at(self, tmp_project):
        """timestamps.updated_at 必填字段缺失时应报错。"""
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["timestamps"] = {}  # 缺少 updated_at
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(
            e.field_name == "timestamps.updated_at" and e.error_type == "missing_field"
            for e in errors
        )

    def test_task_missing_required_field(self, tmp_project):
        """task 结构字段缺失时应报错。"""
        state_file = tmp_project / "pipeline-state.json"
        payload = _valid_pipeline_state()
        payload["tasks"] = {
            "T001": {
                "phase_id": "phase-1",
                # 缺少 executor_type, status, review_status
            },
        }
        state_file.write_text(json.dumps(payload), encoding="utf-8")

        store = PipelineStateStore(state_file)
        _, errors = store.load()
        assert any(
            e.field_name == "tasks.T001.executor_type" and e.error_type == "missing_field"
            for e in errors
        )
        assert any(
            e.field_name == "tasks.T001.status" and e.error_type == "missing_field"
            for e in errors
        )
        assert any(
            e.field_name == "tasks.T001.review_status" and e.error_type == "missing_field"
            for e in errors
        )


# ============================================================
# A04: 任务包 YAML 合法解析
# ============================================================


class TestA04TaskPackageValid:
    """A04: 加载合法任务包 → 返回结构化任务对象。"""

    def test_load_valid_task(self, tmp_project):
        yaml_file = tmp_project / "T001.yaml"
        yaml_file.write_text(
            yaml.dump(_valid_task_yaml(), allow_unicode=True),
            encoding="utf-8",
        )

        loader = TaskPackageLoader()
        pkg, errors = loader.load_file(yaml_file)
        assert not errors
        assert pkg is not None
        assert pkg.id == "T001"
        assert pkg.executor_type == "claude"
        assert pkg.reviewer_type == "governor"
        assert pkg.done_definition == ["build_pass", "acceptance_ready"]
        assert pkg.gate_on_complete == "review_required"
        assert pkg.allowed_write_paths == ["src/governance/"]
        assert pkg.acceptance_refs == ["A01"]

    def test_load_directory(self, tmp_project):
        tasks_dir = tmp_project / "tasks"
        tasks_dir.mkdir()
        for i in range(3):
            task = _valid_task_yaml()
            task["id"] = f"T{i:03d}"
            (tasks_dir / f"T{i:03d}.yaml").write_text(
                yaml.dump(task, allow_unicode=True),
                encoding="utf-8",
            )

        loader = TaskPackageLoader()
        packages, errors = loader.load_directory(tasks_dir)
        assert not errors
        assert len(packages) == 3


# ============================================================
# A05: 任务包 YAML 非法输入
# ============================================================


class TestA05TaskPackageInvalid:
    """A05: 缺失 executor_type 或 allowed_write_paths → 解析失败，错误信息包含字段名。"""

    def test_missing_executor_type(self, tmp_project):
        task = _valid_task_yaml()
        del task["executor_type"]
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text(yaml.dump(task, allow_unicode=True), encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert len(errors) >= 1
        assert any(e.field_name == "executor_type" for e in errors)

    def test_empty_allowed_write_paths(self, tmp_project):
        task = _valid_task_yaml()
        task["allowed_write_paths"] = []
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text(yaml.dump(task, allow_unicode=True), encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert any(e.field_name == "allowed_write_paths" for e in errors)

    def test_empty_acceptance_refs(self, tmp_project):
        task = _valid_task_yaml()
        task["acceptance_refs"] = []
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text(yaml.dump(task, allow_unicode=True), encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert any(e.field_name == "acceptance_refs" for e in errors)

    def test_invalid_executor_type_enum(self, tmp_project):
        task = _valid_task_yaml()
        task["executor_type"] = "worker-agent"
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text(yaml.dump(task, allow_unicode=True), encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert any(e.field_name == "executor_type" and e.error_type == "enum_error" for e in errors)

    def test_invalid_reviewer_type_enum(self, tmp_project):
        task = _valid_task_yaml()
        task["reviewer_type"] = "peer-review"
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text(yaml.dump(task, allow_unicode=True), encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert any(e.field_name == "reviewer_type" and e.error_type == "enum_error" for e in errors)

    def test_invalid_gate_on_complete_enum(self, tmp_project):
        task = _valid_task_yaml()
        task["gate_on_complete"] = "unknown"
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text(yaml.dump(task, allow_unicode=True), encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert any(e.field_name == "gate_on_complete" and e.error_type == "enum_error" for e in errors)

    def test_done_definition_not_array(self, tmp_project):
        task = _valid_task_yaml()
        task["done_definition"] = "single string"
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text(yaml.dump(task, allow_unicode=True), encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert any(e.field_name == "done_definition" and e.error_type == "type_error" for e in errors)

    def test_non_map_yaml(self, tmp_project):
        yaml_file = tmp_project / "bad.yaml"
        yaml_file.write_text("- item1\n- item2\n", encoding="utf-8")

        loader = TaskPackageLoader()
        _, errors = loader.load_file(yaml_file)
        assert any(e.error_type == "schema_error" for e in errors)

    def test_file_not_found(self, tmp_project):
        loader = TaskPackageLoader()
        _, errors = loader.load_file(tmp_project / "missing.yaml")
        assert errors[0].error_type == "file_not_found"


# ============================================================
# A06: 状态机合法流转
# ============================================================


class TestA06StateMachineValidTransitions:
    """A06: drafting -> docs_confirm -> ready_for_dispatch 全部通过。"""

    def test_full_happy_path(self):
        sm = GovernanceStateMachine()
        sm.advance_phase(GovernancePhase.DOCS_CONFIRM)
        sm.advance_phase(GovernancePhase.READY_FOR_DISPATCH)
        sm.advance_phase(GovernancePhase.IN_EXECUTION)
        sm.advance_phase(GovernancePhase.IMPLEMENTATION_REVIEW)
        sm.advance_phase(GovernancePhase.QUALITY_GATE)
        sm.advance_phase(GovernancePhase.ACCEPTED)
        assert sm.phase == GovernancePhase.ACCEPTED

    def test_quality_gate_to_reopened(self):
        sm = GovernanceStateMachine()
        sm.advance_phase(GovernancePhase.DOCS_CONFIRM)
        sm.advance_phase(GovernancePhase.READY_FOR_DISPATCH)
        sm.advance_phase(GovernancePhase.IN_EXECUTION)
        sm.advance_phase(GovernancePhase.IMPLEMENTATION_REVIEW)
        sm.advance_phase(GovernancePhase.QUALITY_GATE)
        sm.advance_phase(GovernancePhase.REOPENED)
        assert sm.phase == GovernancePhase.REOPENED

    def test_reopen_goes_back_to_drafting(self):
        sm = GovernanceStateMachine(phase=GovernancePhase.REOPENED)
        sm.advance_phase(GovernancePhase.DRAFTING)
        assert sm.phase == GovernancePhase.DRAFTING

    def test_gate_transitions(self):
        sm = GovernanceStateMachine()
        sm.transition_gate(GateStatus.BLOCKED)
        sm.transition_gate(GateStatus.OPEN)
        sm.transition_gate(GateStatus.PASSED)
        sm.transition_gate(GateStatus.CLOSED)
        assert sm.gate == GateStatus.CLOSED


# ============================================================
# A07: 状态机非法流转
# ============================================================


class TestA07StateMachineInvalidTransitions:
    """A07: drafting -> quality_gate 明确失败。"""

    def test_drafting_to_quality_gate_blocked(self):
        sm = GovernanceStateMachine()
        with pytest.raises(IllegalTransitionError) as exc_info:
            sm.advance_phase(GovernancePhase.QUALITY_GATE)
        assert "drafting" in str(exc_info.value)
        assert "quality_gate" in str(exc_info.value)

    def test_accepted_has_no_transitions(self):
        sm = GovernanceStateMachine(phase=GovernancePhase.ACCEPTED)
        with pytest.raises(IllegalTransitionError):
            sm.advance_phase(GovernancePhase.DRAFTING)

    def test_skip_phase_blocked(self):
        sm = GovernanceStateMachine()
        with pytest.raises(IllegalTransitionError):
            sm.advance_phase(GovernancePhase.IN_EXECUTION)

    def test_gate_skip_blocked(self):
        sm = GovernanceStateMachine()
        with pytest.raises(IllegalTransitionError):
            sm.transition_gate(GateStatus.CLOSED)

    def test_closed_gate_no_transition(self):
        sm = GovernanceStateMachine(gate=GateStatus.CLOSED)
        with pytest.raises(IllegalTransitionError):
            sm.transition_gate(GateStatus.OPEN)

    def test_can_advance_check(self):
        sm = GovernanceStateMachine()
        assert sm.can_advance_phase(GovernancePhase.DOCS_CONFIRM)
        assert not sm.can_advance_phase(GovernancePhase.QUALITY_GATE)


# ============================================================
# A08: 轮询感知治理变更
# ============================================================


class TestA08PollerDetectsChanges:
    """A08: 修改 pipeline-state.json 或新增任务包 → 一轮周期内感知并刷新内存视图。"""

    def test_detect_new_file(self, tmp_project):
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        (super_dev / "pipeline-state.json").write_text(
            json.dumps(_valid_pipeline_state()), encoding="utf-8",
        )

        poller = GovernancePoller(super_dev)
        changes = poller.scan_once()
        assert any("pipeline-state.json" in c.file_path and c.change_type == "created" for c in changes)

    def test_detect_modification(self, tmp_project):
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        poller = GovernancePoller(super_dev)
        poller.scan_once()

        state_data = _valid_pipeline_state()
        state_data["phases"]["phase-1"]["status"] = "docs_confirm"
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        changes = poller.scan_once()
        assert len(changes) >= 1
        assert any(c.change_type == "modified" for c in changes)

    def test_detect_new_task_yaml(self, tmp_project):
        super_dev = tmp_project / ".super-dev"
        tasks_dir = super_dev / "phases" / "phase-1" / "tasks"
        tasks_dir.mkdir(parents=True)
        (super_dev / "pipeline-state.json").write_text(
            json.dumps(_valid_pipeline_state()), encoding="utf-8",
        )

        poller = GovernancePoller(super_dev)
        poller.scan_once()

        task_file = tasks_dir / "T001.yaml"
        task_file.write_text(
            yaml.dump(_valid_task_yaml(), allow_unicode=True),
            encoding="utf-8",
        )

        changes = poller.scan_once()
        assert any("T001.yaml" in c.file_path for c in changes)

    def test_detect_deletion(self, tmp_project):
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        poller = GovernancePoller(super_dev)
        poller.scan_once()

        state_file.unlink()
        changes = poller.scan_once()
        assert any(c.change_type == "deleted" for c in changes)

    def test_change_log_recorded(self, tmp_project):
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        poller = GovernancePoller(super_dev)
        poller.scan_once()

        state_data = _valid_pipeline_state()
        state_data["phases"]["phase-1"]["status"] = "docs_confirm"
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        poller.scan_once()
        assert len(poller.change_log) >= 1

    def test_reload_success_with_reloader(self, tmp_project):
        """注册 reloader 后，变更文件应触发真实 reload，reload_result 为 success，缓存为实际对象。"""
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        reload_log: list[Path] = []

        def reloader(path: Path) -> tuple[PipelineState, bool]:
            reload_log.append(path)
            store = PipelineStateStore(path)
            state, errors = store.load()
            return (state, len(errors) == 0)

        poller = GovernancePoller(
            super_dev,
            reloaders={"pipeline-state.json": reloader},
        )
        poller.scan_once()

        state_data = _valid_pipeline_state()
        state_data["phases"]["phase-1"]["status"] = "docs_confirm"
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        changes = poller.scan_once()
        modified = [c for c in changes if c.change_type == "modified"]
        assert len(modified) >= 1
        assert modified[0].reload_result == "success"
        assert len(reload_log) >= 1
        # 验证缓存中是实际对象
        cached = poller.get_cache(str(state_file))
        assert cached is not None
        assert isinstance(cached, PipelineState)
        assert cached.get_phase_status("phase-1") == "docs_confirm"

    def test_reload_failure_preserves_old_cache(self, tmp_project):
        """reload 失败时，应记录 reload_result=failed 并保留旧缓存对象。"""
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        call_count = 0
        first_state: PipelineState | None = None

        def failing_reloader(path: Path) -> tuple[PipelineState, bool]:
            nonlocal call_count, first_state
            call_count += 1
            store = PipelineStateStore(path)
            state, errors = store.load()
            if call_count == 1:
                first_state = state
                return (state, True)
            return (state, False)  # 第二次返回失败

        poller = GovernancePoller(
            super_dev,
            reloaders={"pipeline-state.json": failing_reloader},
        )
        poller.scan_once()
        cached_after_first = poller.get_cache(str(state_file))
        assert cached_after_first is not None
        assert isinstance(cached_after_first, PipelineState)
        assert cached_after_first.get_phase_status("phase-1") == "drafting"

        state_data = _valid_pipeline_state()
        state_data["phases"]["phase-1"]["status"] = "docs_confirm"
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        changes = poller.scan_once()
        modified = [c for c in changes if c.change_type == "modified"]
        assert len(modified) >= 1
        assert modified[0].reload_result == "failed"
        assert modified[0].error_reason != ""
        # 验证缓存仍然是旧对象
        cached_after_fail = poller.get_cache(str(state_file))
        assert cached_after_fail is not None
        assert isinstance(cached_after_fail, PipelineState)
        assert cached_after_fail.get_phase_status("phase-1") == "drafting"  # 未更新

    def test_reload_exception_preserves_old_cache(self, tmp_project):
        """reloader 抛异常时，应记录 reload_result=failed 并保留旧缓存对象。"""
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        call_count = 0

        def exception_reloader(path: Path) -> tuple[PipelineState, bool]:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise RuntimeError("disk error")
            store = PipelineStateStore(path)
            state, errors = store.load()
            return (state, len(errors) == 0)

        poller = GovernancePoller(
            super_dev,
            reloaders={"pipeline-state.json": exception_reloader},
        )
        poller.scan_once()
        cached_after_first = poller.get_cache(str(state_file))
        assert cached_after_first is not None
        assert isinstance(cached_after_first, PipelineState)

        state_data = _valid_pipeline_state()
        state_data["phases"]["phase-1"]["status"] = "docs_confirm"
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        changes = poller.scan_once()
        modified = [c for c in changes if c.change_type == "modified"]
        assert modified[0].reload_result == "failed"
        assert "disk error" in modified[0].error_reason
        # 验证缓存仍然是旧对象
        cached_after_fail = poller.get_cache(str(state_file))
        assert cached_after_fail is not None
        assert cached_after_fail.get_phase_status("phase-1") == "drafting"

    def test_no_reloader_records_skipped(self, tmp_project):
        """未注册 reloader 时，reload_result 应为 skipped。"""
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        poller = GovernancePoller(super_dev)
        changes = poller.scan_once()
        assert any(c.reload_result == "skipped" for c in changes)

    def test_background_polling(self, tmp_project):
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        poller = GovernancePoller(super_dev, interval=0.2)
        poller.start()
        try:
            poller.scan_once()
            state_data = _valid_pipeline_state()
            state_data["phases"]["phase-1"]["status"] = "docs_confirm"
            state_file.write_text(json.dumps(state_data), encoding="utf-8")
            time.sleep(0.5)
            assert len(poller.change_log) >= 1
        finally:
            poller.stop()

    def test_on_change_callback(self, tmp_project):
        super_dev = tmp_project / ".super-dev"
        super_dev.mkdir()
        state_file = super_dev / "pipeline-state.json"
        state_file.write_text(json.dumps(_valid_pipeline_state()), encoding="utf-8")

        received: list[ChangeRecord] = []
        poller = GovernancePoller(super_dev, on_change=received.append)
        poller.scan_once()

        state_data = _valid_pipeline_state()
        state_data["phases"]["phase-1"]["status"] = "docs_confirm"
        state_file.write_text(json.dumps(state_data), encoding="utf-8")

        poller.scan_once()
        assert len(received) >= 1
        modified_events = [r for r in received if r.change_type == "modified"]
        assert len(modified_events) >= 1
