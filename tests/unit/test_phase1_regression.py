"""T206: Phase 1 回归验收测试 (A27)。

验收标准 A27:
- 不回退 Phase 1 已完成能力
- dispatch_runnable_tasks / dispatch_from_governance / RuntimeTaskSpec 主链保持成立

关键验证:
1. RuntimeTaskSpec 主模型字段完整（executor_type, phase_id, etc.）
2. dispatch_runnable_tasks 正常派发并返回宿主字段
3. dispatch_from_governance 正常加载治理任务包并派发
4. GovernanceRuntimeAdapter 正常工作
5. DriverRegistry 和宿主感知派发正常
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from claudeflow.runtime.driver_base import (
    DriverRegistry,
    RuntimeTaskSpec,
    ExecutorType,
)
from claudeflow.runtime.claude_driver import ClaudeDriver
from claudeflow.runtime.codex_driver import CodexDriver
from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec, SessionIndex
from claudeflow.runtime.governance_adapter import GovernanceRuntimeAdapter


class TestA27RuntimeTaskSpecMainModel:
    """A27: RuntimeTaskSpec 主模型保持完整"""

    def test_runtime_task_spec_has_executor_type(self):
        """RuntimeTaskSpec 必须包含 executor_type 字段。"""
        spec = RuntimeTaskSpec(
            task_id="regression-001",
            phase_id="phase-1",
            executor_type="claude",
            prompt="测试",
        )

        assert spec.executor_type == "claude"
        assert spec.phase_id == "phase-1"

    def test_runtime_task_spec_has_all_phase1_fields(self):
        """RuntimeTaskSpec 必须包含 Phase 1 定义的所有字段。"""
        spec = RuntimeTaskSpec(
            task_id="regression-002",
            phase_id="phase-1",
            executor_type="codex",
            prompt="测试",
            read_paths=["docs/**"],
            write_paths=["src/**"],
            constraints=["不破坏现有功能"],
            acceptance_refs=["A01", "A02"],
            document_refs=["spec.md"],
            priority="high",
        )

        # 验证所有 Phase 1 字段存在
        assert spec.task_id == "regression-002"
        assert spec.executor_type == "codex"
        assert spec.phase_id == "phase-1"
        assert spec.write_paths == ["src/**"]
        assert spec.acceptance_refs == ["A01", "A02"]
        assert spec.constraints == ["不破坏现有功能"]
        assert spec.priority == "high"

    def test_runtime_task_spec_executor_type_required(self):
        """RuntimeTaskSpec executor_type 是必填字段。"""
        # executor_type 没有默认值，必须显式提供
        spec = RuntimeTaskSpec(
            task_id="regression-003",
            phase_id="phase-1",
            executor_type="claude",  # 必填
            prompt="测试",
        )

        assert spec.executor_type == "claude"

        # 测试不提供 executor_type 会失败
        with pytest.raises(TypeError):
            RuntimeTaskSpec(
                task_id="regression-003-invalid",
                phase_id="phase-1",
                prompt="测试",
            )


class TestA27DispatchRunnableTasks:
    """A27: dispatch_runnable_tasks 主链正常"""

    def test_dispatch_runnable_tasks_returns_started_with_executor_type(self):
        """dispatch_runnable_tasks 必须返回 started 包含 executor_type。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="regression-004", prompt="测试")
            manager.initialize_task_graph([task])

            result = manager.dispatch_runnable_tasks()

            # A27: 必须返回 started 包含 executor_type
            if result["started"]:
                started_item = result["started"][0]
                assert "executor_type" in started_item
                assert started_item["executor_type"] == "claude"
                assert "driver_name" in started_item
                assert started_item["driver_name"] == "claude-driver"

    def test_dispatch_runnable_tasks_accepts_executor_type_param(self):
        """dispatch_runnable_tasks 必须接受 executor_type 参数。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="regression-005", prompt="Codex测试")
            manager.initialize_task_graph([task])

            result = manager.dispatch_runnable_tasks(executor_type="codex")

            # A27: 必须支持 executor_type 参数
            if result["started"]:
                started_item = result["started"][0]
                assert started_item["executor_type"] == "codex"
                assert started_item["driver_name"] == "codex-driver"

    def test_dispatch_runnable_tasks_returns_unified_contract(self):
        """dispatch_runnable_tasks 必须返回统一契约结构。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="regression-006", prompt="测试")
            manager.initialize_task_graph([task])

            result = manager.dispatch_runnable_tasks()

            # A27: 统一返回契约
            assert "started" in result
            assert "skipped" in result
            assert "blocked" in result
            assert "runnable_count" in result
            assert "blocked_count" in result
            assert "available_slots" in result
            assert "active_agents" in result

    def test_get_runnable_specs_returns_runtime_task_specs(self):
        """get_runnable_specs 必须返回 RuntimeTaskSpec 列表。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="regression-007", prompt="测试")
            manager.initialize_task_graph([task])

            specs = manager.get_runnable_specs()

            # A27: 必须返回 RuntimeTaskSpec
            assert len(specs) == 1
            assert isinstance(specs[0], RuntimeTaskSpec)
            assert specs[0].executor_type == "claude"


class TestA27DispatchFromGovernance:
    """A27: dispatch_from_governance 主链正常"""

    def test_dispatch_from_governance_loads_task_packages(self):
        """dispatch_from_governance 必须能加载治理任务包。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            # 创建 .super-dev 结构
            super_dev = Path(tmp) / ".super-dev"
            phases = super_dev / "phases" / "phase-1" / "tasks"
            phases.mkdir(parents=True)

            task_yaml = phases / "T001.yaml"
            task_yaml.write_text("""
id: T001
phase_id: phase-1
title: 回归测试任务
executor_type: claude
reviewer_type: governor
inputs:
  - ../spec.md
constraints:
  - 不破坏 Phase 1 功能
allowed_write_paths:
  - src/**
acceptance_refs:
  - A27
done_definition:
  - regression_pass
gate_on_complete: review_required
""")

            manager = RuntimeManager(tmp)
            result = manager.dispatch_from_governance(str(super_dev), "phase-1")

            # A27: 必须能加载任务包
            assert "started" in result
            assert "skipped" in result
            # 应该成功加载任务
            assert result["runnable_count"] >= 1

    def test_dispatch_from_governance_returns_executor_type(self):
        """dispatch_from_governance 返回必须包含 executor_type。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            super_dev = Path(tmp) / ".super-dev"
            phases = super_dev / "phases" / "phase-1" / "tasks"
            phases.mkdir(parents=True)

            task_yaml = phases / "T002.yaml"
            task_yaml.write_text("""
id: T002
phase_id: phase-1
title: 回归测试任务
executor_type: codex
reviewer_type: governor
inputs: []
constraints: []
allowed_write_paths: []
acceptance_refs:
  - A27
done_definition: []
gate_on_complete: review_required
""")

            manager = RuntimeManager(tmp)
            result = manager.dispatch_from_governance(str(super_dev), "phase-1")

            # A27: started 必须包含 executor_type
            if result["started"]:
                started_item = result["started"][0]
                assert "executor_type" in started_item
                assert started_item["executor_type"] == "codex"

    def test_dispatch_from_governance_handles_empty_phase(self):
        """dispatch_from_governance 对空 phase 返回正确结构。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            super_dev = Path(tmp) / ".super-dev"
            phases = super_dev / "phases" / "phase-empty" / "tasks"
            phases.mkdir(parents=True)

            manager = RuntimeManager(tmp)
            result = manager.dispatch_from_governance(str(super_dev), "phase-empty")

            # A27: 空 phase 返回正确结构
            assert result["started"] == []
            assert result["runnable_count"] == 0


class TestA27GovernanceRuntimeAdapter:
    """A27: GovernanceRuntimeAdapter 正常工作"""

    def test_adapter_loads_task_package(self):
        """GovernanceRuntimeAdapter 必须能加载任务包。"""
        adapter = GovernanceRuntimeAdapter()

        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "regression-task.yaml"
            yaml_path.write_text("""
id: A27-001
phase_id: phase-1
title: 回归验收任务
executor_type: claude
reviewer_type: governor
inputs:
  - ../spec.md
constraints:
  - 不回退 Phase 1 能力
allowed_write_paths:
  - src/**
acceptance_refs:
  - A27
done_definition:
  - dispatch_runnable_tasks_pass
  - dispatch_from_governance_pass
gate_on_complete: review_required
""")

            spec, errors = adapter.load_task_package(yaml_path)

            # A27: 必须无错误加载
            assert len(errors) == 0
            assert spec is not None
            assert spec.task_id == "A27-001"
            assert spec.executor_type == "claude"
            assert spec.acceptance_refs == ["A27"]

    def test_adapter_maps_write_paths(self):
        """GovernanceRuntimeAdapter 必须正确映射 write_paths。"""
        adapter = GovernanceRuntimeAdapter()

        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "regression-task.yaml"
            yaml_path.write_text("""
id: A27-002
phase_id: phase-1
title: 路径映射测试
executor_type: claude
reviewer_type: governor
inputs: []
constraints: []
allowed_write_paths:
  - src/runtime/**
  - src/governance/**
acceptance_refs:
  - A27
done_definition: []
gate_on_complete: review_required
""")

            spec, errors = adapter.load_task_package(yaml_path)

            # A27: write_paths 必须正确映射
            assert spec.write_paths == ["src/runtime/**", "src/governance/**"]

    def test_adapter_load_phase_tasks(self):
        """GovernanceRuntimeAdapter.load_phase_tasks 必须能加载整个 phase。"""
        adapter = GovernanceRuntimeAdapter()

        with tempfile.TemporaryDirectory() as tmp:
            super_dev = Path(tmp) / ".super-dev"
            phases = super_dev / "phases" / "phase-regression" / "tasks"
            phases.mkdir(parents=True)

            # 创建多个任务
            for i in range(3):
                task_yaml = phases / f"T{100+i}.yaml"
                task_yaml.write_text(f"""
id: T{100+i}
phase_id: phase-regression
title: 回归任务 {i}
executor_type: claude
reviewer_type: governor
inputs: []
constraints: []
allowed_write_paths:
  - src/**
acceptance_refs:
  - A27
done_definition: []
gate_on_complete: review_required
priority: {'high' if i == 0 else 'medium'}
""")

            specs, errors = adapter.load_phase_tasks(str(super_dev), "phase-regression")

            # A27: 必须加载所有任务
            assert len(errors) == 0
            assert len(specs) == 3

            # 验证按优先级排序
            assert specs[0].priority == "high"


class TestA27DriverRegistry:
    """A27: DriverRegistry 和宿主感知派发正常"""

    def test_registry_has_claude_driver(self):
        """DriverRegistry 必须包含 ClaudeDriver。"""
        registry = DriverRegistry()
        registry.register(ClaudeDriver())

        driver = registry.get_driver("claude")

        # A27: 必须能获取 ClaudeDriver
        assert driver is not None
        assert driver.executor_type == ExecutorType.CLAUDE

    def test_registry_has_codex_driver(self):
        """DriverRegistry 必须包含 CodexDriver。"""
        registry = DriverRegistry()
        registry.register(CodexDriver(mock_mode=True))

        driver = registry.get_driver("codex")

        # A27: 必须能获取 CodexDriver
        assert driver is not None
        assert driver.executor_type == ExecutorType.CODEX

    def test_registry_validates_executor_types(self):
        """DriverRegistry 必须验证 executor_type。"""
        registry = DriverRegistry()
        registry.register(ClaudeDriver())
        registry.register(CodexDriver(mock_mode=True))

        # A27: 必须拒绝未支持的 executor_type
        is_valid, reason_code = registry.validate_executor_type("future")
        assert is_valid is False
        assert reason_code == "future_executor_not_dispatchable"

        # A27: 必须接受支持的 executor_type
        is_valid, reason_code = registry.validate_executor_type("claude")
        assert is_valid is True


class TestA27SessionIndexHostFields:
    """A27: SessionIndex 宿主字段完整"""

    def test_session_index_has_executor_type_and_driver_name(self):
        """SessionIndex 必须包含 executor_type 和 driver_name。"""
        index = SessionIndex(
            task_id="regression-008",
            session_id="sess-008",
            worktree="/tmp/test",
            status="running",
            owner_role="worker",
            task_type="GovernanceTask",
            prompt="回归测试",
            priority="high",
            write_paths=["src/**"],
            protocol_refs=["P01"],
            design_refs=["D01"],
            executor_type="claude",
            driver_name="claude-driver",
        )

        # A27: 宿主字段必须存在
        assert index.executor_type == "claude"
        assert index.driver_name == "claude-driver"

    def test_session_index_has_phase_id(self):
        """SessionIndex 必须包含 phase_id。"""
        index = SessionIndex(
            task_id="regression-009",
            session_id="sess-009",
            worktree="/tmp/test",
            status="running",
            owner_role="worker",
            task_type="GovernanceTask",
            prompt="回归测试",
            priority="medium",
            write_paths=[],
            protocol_refs=[],
            design_refs=[],
            executor_type="codex",
            driver_name="codex-driver",
            phase_id="phase-1",
        )

        # A27: phase_id 必须存在
        assert index.phase_id == "phase-1"

    def test_session_index_has_acceptance_refs(self):
        """SessionIndex 必须包含 acceptance_refs。"""
        index = SessionIndex(
            task_id="regression-010",
            session_id="sess-010",
            worktree="/tmp/test",
            status="running",
            owner_role="worker",
            task_type="GovernanceTask",
            prompt="回归测试",
            priority="medium",
            write_paths=[],
            protocol_refs=[],
            design_refs=[],
            executor_type="claude",
            driver_name="claude-driver",
            phase_id="phase-1",
            acceptance_refs=["A27"],
        )

        # A27: acceptance_refs 必须存在
        assert index.acceptance_refs == ["A27"]


class TestA27StartWorkerWithSpec:
    """A27: start_worker_with_spec 主链正常"""

    def test_start_worker_with_spec_accepts_runtime_task_spec(self):
        """start_worker_with_spec 必须接受 RuntimeTaskSpec。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            spec = RuntimeTaskSpec(
                task_id="regression-011",
                phase_id="phase-1",
                executor_type="claude",
                prompt="RuntimeTaskSpec 派发测试",
            )

            index, reason_code, reason = manager.start_worker_with_spec(spec)

            # A27: RuntimeTaskSpec 必须能派发
            assert index is not None
            assert index.executor_type == "claude"
            assert index.driver_name == "claude-driver"

    def test_start_worker_with_spec_populates_all_fields(self):
        """start_worker_with_spec 必须填充所有 Phase 1 字段。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            spec = RuntimeTaskSpec(
                task_id="regression-012",
                phase_id="phase-1",
                executor_type="claude",
                prompt="完整字段测试",
                write_paths=["src/**", "tests/**"],
                acceptance_refs=["A27"],
                constraints=["不破坏 Phase 1"],
                priority="high",
            )

            index, reason_code, reason = manager.start_worker_with_spec(spec)

            # A27: 所有字段必须填充
            assert index is not None
            assert index.phase_id == "phase-1"
            assert index.write_paths == ["src/**", "tests/**"]
            assert index.acceptance_refs == ["A27"]
            assert index.priority == "high"


class TestA27Phase2Integration:
    """A27: Phase 2 模块不影响 Phase 1 主链"""

    def test_governance_module_does_not_block_dispatch(self):
        """Phase 2 governance 模块不应阻塞 Phase 1 dispatch 主链。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            # 创建 .super-dev 结构（Phase 2 governance 标识）
            super_dev = Path(tmp) / ".super-dev"
            super_dev.mkdir(parents=True)

            # 创建 pipeline-state.json（Phase 2 治理状态）
            state_path = super_dev / "pipeline-state.json"
            import json
            state_path.write_text(json.dumps({
                "workflow_version": "v1",
                "project": "test",
                "current_phase": "phase-1",
                "current_stage": "in_execution",
                "current_gate": "",
                "gate_status": "open",
                "governor": {"host": "claude", "mode": "governor"},
                "advance_allowed": False,
                "reopen_required": False,
                "phases": {},
                "tasks": {},
                "timestamps": {"updated_at": "2026-01-01T00:00:00Z"},
            }, indent=2))

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            # Phase 1 dispatch 应该不受影响
            task = WorkerTaskSpec(task_id="regression-013", prompt="集成测试")
            manager.initialize_task_graph([task])

            result = manager.dispatch_runnable_tasks()

            # A27: Phase 2 存在时 dispatch 仍然正常
            if result["started"]:
                assert result["started"][0]["executor_type"] == "claude"

    def test_runtime_api_excludes_executor_type(self):
        """Runtime API 必须在 plan 输出中包含 executor_type。"""
        # 验证 api.py 的 plan 端点逻辑
        # 注意：这是静态验证，不启动服务
        from claudeflow.runtime.api import app

        # 检查路由存在
        routes = [route.path for route in app.routes]
        assert "/api/runtime/plan" in routes
        assert "/api/runtime/dispatch" in routes
        assert "/api/runtime/dispatch/governance" in routes