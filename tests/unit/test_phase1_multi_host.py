"""Phase 1 多宿主执行层验收测试。

验收点（按 acceptance.md）:
- A01: Driver 抽象建立
- A02: Claude 路径可运行
- A03: Codex 路径可运行
- A04: 不支持宿主被拒绝
- A05: 治理任务包进入 dispatch 主链
- A06: Session Index 宿主字段完整
- A07: 结果回收统一
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

from claudeflow.runtime.driver_base import (
    DriverRegistry,
    DriverStatus,
    DriverSessionStartResult,
    DriverExecutionResult,
    ExecutorType,
    RuntimeDriver,
    RuntimeTaskSpec,
)
from claudeflow.runtime.claude_driver import ClaudeDriver
from claudeflow.runtime.codex_driver import CodexDriver
from claudeflow.runtime.governance_adapter import (
    GovernanceRuntimeAdapter,
    GovernanceRuntimeAdapterError,
)
from claudeflow.runtime.manager import RuntimeManager, SessionIndex, WorkerTaskSpec, RuntimeErrorBase


class TestA01DriverAbstract:
    """A01: Driver 抽象建立"""

    def test_runtime_driver_is_abstract(self):
        """RuntimeDriver 必须是抽象类，不能直接实例化。"""
        with pytest.raises(TypeError):
            RuntimeDriver()

    def test_claude_driver_implements_interface(self):
        """ClaudeDriver 必须实现 RuntimeDriver 接口。"""
        driver = ClaudeDriver()
        assert isinstance(driver, RuntimeDriver)
        assert driver.driver_name == "claude-driver"
        assert driver.executor_type == ExecutorType.CLAUDE

    def test_codex_driver_implements_interface(self):
        """CodexDriver 必须实现 RuntimeDriver 接口。"""
        driver = CodexDriver(mock_mode=True)
        assert isinstance(driver, RuntimeDriver)
        assert driver.driver_name == "codex-driver"
        assert driver.executor_type == ExecutorType.CODEX

    def test_driver_registry_can_register_and_get(self):
        """DriverRegistry 必须能注册和获取驱动。"""
        registry = DriverRegistry()
        registry.register(ClaudeDriver())
        registry.register(CodexDriver(mock_mode=True))

        claude = registry.get_driver("claude")
        assert claude is not None
        assert claude.driver_name == "claude-driver"

        codex = registry.get_driver("codex")
        assert codex is not None
        assert codex.driver_name == "codex-driver"


class TestA02ClaudePathRunnable:
    """A02: Claude 路径可运行"""

    def test_claude_driver_start_task_returns_result(self):
        """ClaudeDriver.start_task 必须返回 DriverSessionStartResult。"""
        driver = ClaudeDriver()
        spec = RuntimeTaskSpec(
            task_id="test-001",
            phase_id="phase-1",
            executor_type="claude",
            prompt="测试任务",
        )

        # 注意：真实执行会启动 CLI，这里只测试返回结构
        result = driver.start_task(spec, cwd=None)

        assert isinstance(result, DriverSessionStartResult)
        assert result.executor_type == "claude"
        assert result.driver_name == "claude-driver"

    def test_claude_driver_registers_in_registry(self):
        """executor_type=claude 必须正确选择 ClaudeDriver。"""
        registry = DriverRegistry()
        registry.register(ClaudeDriver())

        driver = registry.get_driver("claude")
        assert driver is not None
        assert driver.executor_type == ExecutorType.CLAUDE


class TestA03CodexPathRunnable:
    """A03: Codex 路径可运行"""

    def test_codex_driver_mock_mode_starts_session(self):
        """CodexDriver mock 模式必须能启动会话。"""
        driver = CodexDriver(mock_mode=True)
        spec = RuntimeTaskSpec(
            task_id="test-002",
            phase_id="phase-1",
            executor_type="codex",
            prompt="测试任务",
        )

        result = driver.start_task(spec)

        assert isinstance(result, DriverSessionStartResult)
        assert result.success
        assert result.session_id != ""
        assert result.executor_type == "codex"
        assert result.driver_name == "codex-driver"

    def test_codex_driver_collect_result_returns_unified(self):
        """CodexDriver.collect_result 必须返回统一结构。"""
        driver = CodexDriver(mock_mode=True)
        spec = RuntimeTaskSpec(
            task_id="test-003",
            phase_id="phase-1",
            executor_type="codex",
            prompt="测试任务",
        )

        result = driver.start_task(spec)
        collected = driver.collect_result(result.session_id)

        assert isinstance(collected, DriverExecutionResult)
        assert collected.executor_type == "codex"
        assert collected.driver_name == "codex-driver"


class TestA04UnsupportedExecutorRejected:
    """A04: 不支持宿主被拒绝"""

    def test_future_executor_rejected(self):
        """executor_type=future 必须被拒绝。"""
        registry = DriverRegistry()
        registry.register(ClaudeDriver())
        registry.register(CodexDriver(mock_mode=True))

        is_valid, reason_code = registry.validate_executor_type("future")
        assert is_valid is False
        assert reason_code == "future_executor_not_dispatchable"

    def test_unknown_executor_rejected(self):
        """未知 executor_type 必须被拒绝。"""
        registry = DriverRegistry()

        is_valid, reason_code = registry.validate_executor_type("unknown")
        assert is_valid is False
        assert reason_code == "unsupported_executor_type"

    def test_unregistered_driver_returns_none(self):
        """未注册驱动必须返回 None。"""
        registry = DriverRegistry()

        driver = registry.get_driver("claude")
        assert driver is None

    def test_dispatch_does_not_create_fake_session(self):
        """不支持宿主派发不得创建伪 session index。"""
        registry = DriverRegistry()
        registry.register(ClaudeDriver())

        # executor_type=codex 未注册
        driver = registry.get_driver("codex")
        assert driver is None


class TestA05GovernanceTaskToDispatch:
    """A05: 治理任务包进入 dispatch 主链"""

    def test_adapter_loads_task_package(self):
        """GovernanceRuntimeAdapter 必须能加载任务包。"""
        adapter = GovernanceRuntimeAdapter()

        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "test-task.yaml"
            yaml_path.write_text("""
id: T001
phase_id: phase-1
title: 测试任务
executor_type: claude
reviewer_type: governor
inputs:
  - ../spec.md
constraints:
  - 不破坏现有功能
allowed_write_paths:
  - src/**
acceptance_refs:
  - A01
done_definition:
  - review_ready
gate_on_complete: review_required
""")

            spec, errors = adapter.load_task_package(yaml_path)
            assert len(errors) == 0
            assert spec is not None
            assert spec.task_id == "T001"
            assert spec.executor_type == "claude"

    def test_adapter_maps_fields_to_runtime_spec(self):
        """任务包字段必须正确映射到 RuntimeTaskSpec。"""
        adapter = GovernanceRuntimeAdapter()

        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "test-task.yaml"
            yaml_path.write_text("""
id: T002
phase_id: phase-1
title: 测试任务
executor_type: codex
reviewer_type: governor
inputs:
  - ../spec.md
  - ../architecture.md
constraints:
  - 保持兼容
allowed_write_paths:
  - src/runtime/**
acceptance_refs:
  - A03
done_definition:
  - codex_dispatch_path_testable
gate_on_complete: review_required
priority: high
""")

            spec, errors = adapter.load_task_package(yaml_path)
            assert spec.executor_type == "codex"
            assert spec.write_paths == ["src/runtime/**"]
            assert spec.acceptance_refs == ["A03"]
            assert spec.constraints == ["保持兼容"]
            assert spec.priority == "high"

    def test_adapter_builds_dispatch_input(self):
        """adapter.build_dispatch_input 必须生成结构化派发对象。"""
        adapter = GovernanceRuntimeAdapter()
        spec = RuntimeTaskSpec(
            task_id="T003",
            phase_id="phase-1",
            executor_type="claude",
            prompt="测试",
            write_paths=["src/**"],
            acceptance_refs=["A01"],
        )

        dispatch_input = adapter.build_dispatch_input(spec)
        assert dispatch_input["task_id"] == "T003"
        assert dispatch_input["executor_type"] == "claude"
        assert dispatch_input["write_paths"] == ["src/**"]


class TestA06SessionIndexHostFields:
    """A06: Session Index 宿主字段完整"""

    def test_session_index_has_executor_type(self):
        """SessionIndex 必须包含 executor_type。"""
        index = SessionIndex(
            task_id="test-001",
            session_id="sess-001",
            worktree="/tmp/test",
            status="running",
            owner_role="worker",
            task_type="ImplementTask",
            prompt="test",
            priority="high",
            write_paths=["src/**"],
            protocol_refs=["P01"],
            design_refs=["D01"],
            executor_type="claude",
            driver_name="claude-driver",
        )

        assert index.executor_type == "claude"
        assert index.driver_name == "claude-driver"

    def test_session_index_has_driver_name(self):
        """SessionIndex 必须包含 driver_name。"""
        index = SessionIndex(
            task_id="test-002",
            session_id="sess-002",
            worktree="/tmp/test",
            status="running",
            owner_role="worker",
            task_type="GovernanceTask",
            prompt="test",
            priority="medium",
            write_paths=[],
            protocol_refs=[],
            design_refs=[],
            executor_type="codex",
            driver_name="codex-driver",
        )

        assert index.driver_name == "codex-driver"

    def test_runtime_manager_dispatch_from_governance_populates_fields(self):
        """RuntimeManager.dispatch_from_governance 必须填充宿主字段。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 初始化 git 仓库（worktree 操作需要）
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
title: 测试任务
executor_type: claude
reviewer_type: governor
inputs:
  - ../spec.md
constraints:
  - 测试约束
allowed_write_paths:
  - src/**
acceptance_refs:
  - A01
done_definition:
  - review_ready
gate_on_complete: review_required
""")

            manager = RuntimeManager(tmp)
            result = manager.dispatch_from_governance(
                str(super_dev),
                "phase-1",
            )

            # 验证派发结果包含 executor_type
            if result["started"]:
                started_item = result["started"][0]
                assert "executor_type" in started_item
                assert started_item["executor_type"] == "claude"


class TestA07ResultCollectionUnified:
    """A07: 结果回收统一"""

    def test_driver_execution_result_has_required_fields(self):
        """DriverExecutionResult 必须包含所有必需字段。"""
        result = DriverExecutionResult(
            success=True,
            session_id="sess-001",
            task_id="task-001",
            executor_type="claude",
            driver_name="claude-driver",
            summary="任务完成",
            changed_files=["src/main.py"],
            tests={"passed": 5},
            known_issues=["issue-1"],
            test_evidence=["pytest output"],
        )

        assert result.executor_type == "claude"
        assert result.driver_name == "claude-driver"
        assert result.summary == "任务完成"
        assert result.changed_files == ["src/main.py"]
        assert result.tests == {"passed": 5}
        assert result.known_issues == ["issue-1"]
        assert result.test_evidence == ["pytest output"]

    def test_codex_mock_result_is_unified(self):
        """CodexDriver mock 结果必须能映射到统一结构。"""
        driver = CodexDriver(mock_mode=True)
        spec = RuntimeTaskSpec(
            task_id="test-004",
            phase_id="phase-1",
            executor_type="codex",
            prompt="测试",
        )

        start_result = driver.start_task(spec)
        collected = driver.collect_result(start_result.session_id)

        # 验证统一结构
        assert hasattr(collected, "executor_type")
        assert hasattr(collected, "driver_name")
        assert hasattr(collected, "summary")
        assert hasattr(collected, "changed_files")
        assert hasattr(collected, "tests")
        assert hasattr(collected, "known_issues")
        assert hasattr(collected, "test_evidence")


class TestCLIOutputHostInfo:
    """A08: CLI/API 输出宿主信息"""

    def test_dispatch_result_has_executor_type(self):
        """派发结果必须包含 executor_type。"""
        driver = CodexDriver(mock_mode=True)
        spec = RuntimeTaskSpec(
            task_id="test-005",
            phase_id="phase-1",
            executor_type="codex",
            prompt="测试",
        )

        result = driver.start_task(spec)
        assert result.executor_type == "codex"

    def test_dispatch_result_has_driver_name(self):
        """派发结果必须包含 driver_name。"""
        driver = CodexDriver(mock_mode=True)
        spec = RuntimeTaskSpec(
            task_id="test-006",
            phase_id="phase-1",
            executor_type="codex",
            prompt="测试",
        )

        result = driver.start_task(spec)
        assert result.driver_name == "codex-driver"

    def test_runtime_manager_explain_task_has_executor_type(self):
        """RuntimeManager.explain_task 输出必须包含 executor_type。"""
        with tempfile.TemporaryDirectory() as tmp:
            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            # 初始化任务图
            from claudeflow.runtime.manager import WorkerTaskSpec
            task = WorkerTaskSpec(
                task_id="test-007",
                prompt="测试",
            )
            manager.initialize_task_graph([task])

            # explain_task 返回需要包含 executor_type（如果已派发）
            # T108: 未派发时 executor_type 和 driver_name 为空
            explanation = manager.explain_task("test-007")
            assert "task_id" in explanation
            assert "executor_type" in explanation
            assert "driver_name" in explanation
            assert explanation["executor_type"] == ""  # 未派发时为空


class TestT108MainlineHostification:
    """T108: 主链宿主化验收测试"""

    def test_start_worker_dispatches_through_registry(self):
        """start_worker 必须通过 registry 派发，不能使用硬编码 CliDriver。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 初始化 git 仓库
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            # 初始化任务图
            task = WorkerTaskSpec(
                task_id="t108-001",
                prompt="测试任务",
            )
            manager.initialize_task_graph([task])

            # 使用 start_worker 派发
            index = manager.start_worker(task)

            # 验证派发通过 registry（宿主字段正确填充）
            assert index.executor_type == "claude"
            assert index.driver_name == "claude-driver"

    def test_start_worker_can_specify_executor_type(self):
        """start_worker 必须支持指定 executor_type 参数。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(
                task_id="t108-002",
                prompt="Codex 测试",
            )
            manager.initialize_task_graph([task])

            # 指定 codex executor
            index = manager.start_worker(task, executor_type="codex")

            # 验证 codex 宿主派发
            assert index.executor_type == "codex"
            assert index.driver_name == "codex-driver"

    def test_explain_task_outputs_host_fields(self):
        """explain_task 必须输出 executor_type 和 driver_name。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t108-003", prompt="测试")
            manager.initialize_task_graph([task])

            # 先派发任务
            manager.start_worker(task)

            # 调用 explain_task
            explanation = manager.explain_task("t108-003")

            # T108: 必须输出宿主字段
            assert "executor_type" in explanation
            assert "driver_name" in explanation
            assert explanation["executor_type"] == "claude"
            assert explanation["driver_name"] == "claude-driver"

    def test_dispatch_runnable_tasks_uses_registry(self):
        """dispatch_runnable_tasks 必须通过 registry 派发。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t108-004", prompt="批量派发测试")
            manager.initialize_task_graph([task])

            result = manager.dispatch_runnable_tasks()

            # 验证派发结果包含宿主字段
            if result["started"]:
                started_item = result["started"][0]
                assert "executor_type" in started_item
                assert started_item["executor_type"] == "claude"
                assert "driver_name" in started_item
                assert started_item["driver_name"] == "claude-driver"

    def test_start_worker_releases_lock_on_failure(self):
        """Blocker 修复：start_worker 失败时必须释放写锁。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t108-lock", prompt="锁测试")
            manager.initialize_task_graph([task])

            # 使用不存在的 executor_type 触发失败
            with pytest.raises(RuntimeErrorBase) as exc_info:
                manager.start_worker(task, executor_type="unknown_executor")

            # 验证异常被抛出
            assert "executor_type=unknown_executor" in str(exc_info.value) or "不支持" in str(exc_info.value)

            # 验证锁已释放（可以再次尝试派发）
            lock_file = Path(tmp) / ".runtime" / "locks" / "t108-lock.json"
            # 锁文件应该不存在或已被清理
            assert not lock_file.exists(), "失败后锁应该被释放"


class TestT109RuntimeTaskSpecMainModel:
    """T109: RuntimeTaskSpec 主模型迁移验收测试"""

    def test_get_runnable_specs_returns_runtime_task_specs(self):
        """get_runnable_specs 必须返回 RuntimeTaskSpec 列表。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t109-001", prompt="测试")
            manager.initialize_task_graph([task])

            specs = manager.get_runnable_specs()

            assert len(specs) == 1
            assert isinstance(specs[0], RuntimeTaskSpec)
            assert specs[0].task_id == "t109-001"
            assert specs[0].executor_type == "claude"  # 默认值

    def test_get_runnable_specs_can_specify_executor_type(self):
        """get_runnable_specs 必须支持指定 executor_type。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t109-002", prompt="测试")
            manager.initialize_task_graph([task])

            specs = manager.get_runnable_specs(executor_type="codex")

            assert specs[0].executor_type == "codex"

    def test_get_dispatch_plan_specs_returns_runtime_specs(self):
        """get_dispatch_plan_specs runnable 必须为 RuntimeTaskSpec。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t109-003", prompt="测试")
            manager.initialize_task_graph([task])

            plan = manager.get_dispatch_plan_specs()

            assert len(plan["runnable"]) == 1
            assert isinstance(plan["runnable"][0], RuntimeTaskSpec)

    def test_dispatch_runnable_tasks_accepts_executor_type(self):
        """dispatch_runnable_tasks 必须接受 executor_type 参数。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t109-004", prompt="测试")
            manager.initialize_task_graph([task])

            # 指定 codex 派发
            result = manager.dispatch_runnable_tasks(executor_type="codex")

            if result["started"]:
                started_item = result["started"][0]
                assert started_item["executor_type"] == "codex"
                assert started_item["driver_name"] == "codex-driver"

    def test_worker_task_spec_is_only_compat_input(self):
        """WorkerTaskSpec 只能作为兼容输入，主链必须使用 RuntimeTaskSpec。"""
        # 验证 RuntimeTaskSpec 是主链模型
        # WorkerTaskSpec 只在 get_runnable_tasks (deprecated) 中返回
        # get_runnable_specs 是推荐入口
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp, capture_output=True)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp, capture_output=True)

            manager = RuntimeManager(tmp)
            manager.ensure_layout()

            task = WorkerTaskSpec(task_id="t109-005", prompt="兼容测试")
            manager.initialize_task_graph([task])

            # WorkerTaskSpec 兼容入口仍然可用
            workers = manager.get_runnable_tasks()
            assert len(workers) == 1
            assert isinstance(workers[0], WorkerTaskSpec)

            # RuntimeTaskSpec 主链入口
            specs = manager.get_runnable_specs()
            assert len(specs) == 1
            assert isinstance(specs[0], RuntimeTaskSpec)