"""多会话运行时管理器测试。"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestRuntimeManagerLayout:
    def test_initialize_task_graph_creates_runtime_layout(self):
        from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuntimeManager(repo_path=tmpdir)
            manager.initialize_task_graph(
                [
                    WorkerTaskSpec(task_id="task_a", prompt="实现A"),
                    WorkerTaskSpec(task_id="task_b", prompt="实现B"),
                ]
            )

            runtime_dir = Path(tmpdir) / ".claudeflow"
            assert runtime_dir.exists()
            assert (runtime_dir / "runtime-status.json").exists()
            assert (runtime_dir / "task-graph.json").exists()
            assert (runtime_dir / "sessions").exists()
            assert (runtime_dir / "locks").exists()

            status = manager._load_runtime_status()
            assert status["queued_tasks"] == 2
            assert status["active_agents"] == 0

    def test_load_task_graph_from_file(self):
        from claudeflow.runtime.manager import RuntimeManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuntimeManager(repo_path=tmpdir)
            task_graph_path = Path(tmpdir) / "task-graph-input.json"
            task_graph_path.write_text(
                """
{
  "tasks": [
    {
      "task_id": "impl_auth_controller",
      "prompt": "实现 AuthController",
      "owner_role": "backend-agent",
      "task_type": "ImplementTask",
      "write_paths": ["src/controllers/AuthController.java"],
      "protocol_refs": ["auth_api@v2"]
    }
  ]
}
                """.strip(),
                encoding="utf-8",
            )

            tasks = manager.load_task_graph(str(task_graph_path))

            assert len(tasks) == 1
            assert tasks[0].task_id == "impl_auth_controller"
            assert tasks[0].protocol_refs == ["auth_api@v2"]
            assert tasks[0].priority == "medium"

    def test_load_task_graph_invalid_payload_raises(self):
        from claudeflow.runtime.manager import RuntimeManager, TaskGraphValidationError

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuntimeManager(repo_path=tmpdir)
            task_graph_path = Path(tmpdir) / "invalid-task-graph.json"
            task_graph_path.write_text('{"tasks": [{"task_id": "missing_prompt"}]}', encoding="utf-8")

            with pytest.raises(TaskGraphValidationError):
                manager.load_task_graph(str(task_graph_path))


class TestRuntimeManagerWorkers:
    def test_start_worker_creates_worktree_session_and_runtime_status(self):
        from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.return_value = (Mock(), "sess-123")
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            task = WorkerTaskSpec(
                task_id="impl_auth_controller",
                prompt="实现 AuthController",
                write_paths=["src/controllers/AuthController.java"],
                protocol_refs=["auth_api@v2"],
                design_refs=["architecture@v2"],
            )
            manager.initialize_task_graph([task])

            with patch("claudeflow.runtime.manager.subprocess.run") as mock_run:
                index = manager.start_worker(task)

            assert index.session_id == "sess-123"
            assert index.status == "running"
            assert Path(index.worktree).name == "impl_auth_controller"
            driver.start_session.assert_called_once()
            assert driver.start_session.call_args.kwargs["cwd"].endswith("impl_auth_controller")
            mock_run.assert_called_once()

            stored = manager.get_session_index("impl_auth_controller")
            assert stored["session_id"] == "sess-123"
            assert stored["protocol_refs"] == ["auth_api@v2"]

            status = manager._load_runtime_status()
            assert status["active_agents"] == 1
            assert status["queued_tasks"] == 0
            assert status["running_tasks"] == ["impl_auth_controller"]

    def test_complete_worker_writes_checkpoint_and_releases_lock(self):
        from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.return_value = (Mock(), "sess-123")
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            task = WorkerTaskSpec(
                task_id="impl_auth_controller",
                prompt="实现 AuthController",
                write_paths=["src/controllers/AuthController.java"],
            )
            manager.initialize_task_graph([task])

            with patch("claudeflow.runtime.manager.subprocess.run"):
                manager.start_worker(task)

            index = manager.complete_worker(
                "impl_auth_controller",
                summary="Controller 已实现",
                changed_files=["src/controllers/AuthController.java"],
                tests={"status": "passed", "count": 3},
            )

            assert index["status"] == "completed"
            checkpoint_path = Path(tmpdir) / ".claudeflow" / "checkpoints" / "impl_auth_controller.json"
            assert checkpoint_path.exists()
            lock_path = Path(tmpdir) / ".claudeflow" / "locks" / "impl_auth_controller.json"
            assert not lock_path.exists()

            status = manager._load_runtime_status()
            assert status["active_agents"] == 0
            assert status["completed_tasks"] == 1

    def test_fail_worker_marks_failed_and_sets_intervention_required(self):
        from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.return_value = (Mock(), "sess-123")
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            task = WorkerTaskSpec(
                task_id="impl_auth_controller",
                prompt="实现 AuthController",
                write_paths=["src/controllers/AuthController.java"],
            )
            manager.initialize_task_graph([task])

            with patch("claudeflow.runtime.manager.subprocess.run"):
                manager.start_worker(task)

            index = manager.fail_worker("impl_auth_controller", "测试失败，需要人工介入")

            assert index["status"] == "failed"
            assert index["summary"] == "测试失败，需要人工介入"
            checkpoint_path = Path(tmpdir) / ".claudeflow" / "checkpoints" / "impl_auth_controller.json"
            assert checkpoint_path.exists()
            lock_path = Path(tmpdir) / ".claudeflow" / "locks" / "impl_auth_controller.json"
            assert not lock_path.exists()

            status = manager._load_runtime_status()
            assert status["failed_tasks"] == 1
            assert status["intervention_required"] is True

    def test_get_runnable_tasks_after_completion_returns_new_ready_nodes(self):
        from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.side_effect = [
                (Mock(), "sess-a"),
                (Mock(), "sess-b"),
            ]
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            tasks = [
                WorkerTaskSpec(task_id="task_a", prompt="实现A"),
                WorkerTaskSpec(task_id="task_b", prompt="实现B", depends_on=["task_a"]),
            ]
            manager.initialize_task_graph(tasks)

            with patch("claudeflow.runtime.manager.subprocess.run"):
                manager.start_worker(tasks[0])

            manager.complete_worker("task_a", summary="A 已完成")
            runnable = manager.get_runnable_tasks()

            assert [task.task_id for task in runnable] == ["task_b"]

    def test_dispatch_runnable_tasks_starts_only_dependency_free_nodes(self):
        from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.side_effect = [
                (Mock(), "sess-a"),
                (Mock(), "sess-b"),
            ]
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            tasks = [
                WorkerTaskSpec(task_id="task_a", prompt="实现A"),
                WorkerTaskSpec(task_id="task_b", prompt="实现B", depends_on=["task_a"]),
            ]
            manager.initialize_task_graph(tasks)

            with patch("claudeflow.runtime.manager.subprocess.run"):
                result = manager.dispatch_runnable_tasks()

            assert result["runnable_count"] == 1
            assert len(result["started"]) == 1
            assert result["started"][0]["task_id"] == "task_a"

    def test_dispatch_runnable_tasks_sorts_by_priority(self):
        from claudeflow.runtime.manager import RuntimeManager, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.side_effect = [
                (Mock(), "sess-high"),
                (Mock(), "sess-medium"),
            ]
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            tasks = [
                WorkerTaskSpec(task_id="task_b", prompt="实现B", priority="medium"),
                WorkerTaskSpec(task_id="task_a", prompt="实现A", priority="high"),
            ]
            manager.initialize_task_graph(tasks)

            with patch("claudeflow.runtime.manager.subprocess.run"):
                result = manager.dispatch_runnable_tasks()

            assert [item["task_id"] for item in result["started"]] == ["task_a", "task_b"]

    def test_dispatch_runnable_tasks_reports_blocked_reasons(self):
        from claudeflow.runtime.manager import RuntimeManager, RuntimeReasonCode, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.return_value = (Mock(), "sess-a")
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            tasks = [
                WorkerTaskSpec(task_id="task_a", prompt="实现A", priority="high"),
                WorkerTaskSpec(task_id="task_b", prompt="实现B", depends_on=["task_a"], priority="low"),
                WorkerTaskSpec(task_id="task_c", prompt="实现C", depends_on=["missing_task"], priority="medium"),
            ]
            manager.initialize_task_graph(tasks)

            with patch("claudeflow.runtime.manager.subprocess.run"):
                result = manager.dispatch_runnable_tasks(limit=1)

            assert result["runnable_count"] == 1
            assert result["blocked_count"] == 2
            reasons = {item["task_id"]: item["reason"] for item in result["blocked"]}
            codes = {item["task_id"]: item["reason_code"] for item in result["blocked"]}
            assert "等待依赖完成" in reasons["task_b"]
            assert "依赖任务不存在" in reasons["task_c"]
            assert codes["task_b"] == RuntimeReasonCode.WAITING_DEPENDENCY
            assert codes["task_c"] == RuntimeReasonCode.MISSING_DEPENDENCY

    def test_dispatch_plan_blocks_downstream_when_dependency_failed(self):
        from claudeflow.runtime.manager import RuntimeManager, RuntimeReasonCode, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.return_value = (Mock(), "sess-a")
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            tasks = [
                WorkerTaskSpec(task_id="task_a", prompt="实现A"),
                WorkerTaskSpec(task_id="task_b", prompt="实现B", depends_on=["task_a"]),
            ]
            manager.initialize_task_graph(tasks)

            with patch("claudeflow.runtime.manager.subprocess.run"):
                manager.start_worker(tasks[0])

            manager.fail_worker("task_a", "失败")
            plan = manager.get_dispatch_plan()

            assert not plan["runnable"]
            assert plan["blocked"][0]["task_id"] == "task_b"
            assert plan["blocked"][0]["reason_code"] == RuntimeReasonCode.UPSTREAM_FAILED
            assert "上游失败" in plan["blocked"][0]["reason"]

    def test_dispatch_respects_max_concurrent_slots(self):
        from claudeflow.runtime.manager import RuntimeManager, RuntimeReasonCode, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.return_value = (Mock(), "sess-a")
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            tasks = [
                WorkerTaskSpec(task_id="task_a", prompt="实现A", priority="high"),
                WorkerTaskSpec(task_id="task_b", prompt="实现B", priority="medium"),
            ]
            manager.initialize_task_graph(tasks)

            with patch("claudeflow.runtime.manager.subprocess.run"):
                result = manager.dispatch_runnable_tasks(max_concurrent=1)

            assert len(result["started"]) == 1
            assert result["started"][0]["task_id"] == "task_a"
            assert result["available_slots"] == 1
            reasons = {item["task_id"]: item["reason"] for item in result["blocked"]}
            codes = {item["task_id"]: item["reason_code"] for item in result["blocked"]}
            assert reasons["task_b"] == "等待可用并发槽位"
            assert codes["task_b"] == RuntimeReasonCode.WAITING_SLOT

    def test_explain_task_returns_blocked_reason(self):
        from claudeflow.runtime.manager import RuntimeManager, RuntimeReasonCode, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuntimeManager(repo_path=tmpdir)
            tasks = [
                WorkerTaskSpec(task_id="task_a", prompt="实现A"),
                WorkerTaskSpec(task_id="task_b", prompt="实现B", depends_on=["task_a"], priority="high"),
            ]
            manager.initialize_task_graph(tasks)

            explanation = manager.explain_task("task_b")

            assert explanation["state"] == "blocked"
            assert explanation["priority"] == "high"
            assert explanation["reason_code"] == RuntimeReasonCode.WAITING_DEPENDENCY
            assert "等待依赖完成" in explanation["reason"]

    def test_dispatch_plan_includes_running_items(self):
        from claudeflow.runtime.manager import RuntimeManager, RuntimeReasonCode, WorkerTaskSpec

        with tempfile.TemporaryDirectory() as tmpdir:
            driver = Mock()
            driver.start_session.return_value = (Mock(), "sess-a")
            manager = RuntimeManager(repo_path=tmpdir, driver=driver)
            tasks = [
                WorkerTaskSpec(task_id="task_a", prompt="实现A", priority="high"),
                WorkerTaskSpec(task_id="task_b", prompt="实现B", priority="low"),
            ]
            manager.initialize_task_graph(tasks)

            with patch("claudeflow.runtime.manager.subprocess.run"):
                manager.start_worker(tasks[0])

            plan = manager.get_dispatch_plan()

            assert plan["running"][0]["task_id"] == "task_a"
            assert plan["running"][0]["reason_code"] == RuntimeReasonCode.SESSION_RUNNING


class TestRuntimeManagerLocks:
    def test_acquire_write_lock_detects_conflict(self):
        from claudeflow.runtime.manager import (
            RuntimeManager,
            WorkerTaskSpec,
            WriteLockConflictError,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RuntimeManager(repo_path=tmpdir)
            task_a = WorkerTaskSpec(
                task_id="task_a",
                prompt="实现A",
                write_paths=["src/shared/UserService.java"],
            )
            task_b = WorkerTaskSpec(
                task_id="task_b",
                prompt="实现B",
                write_paths=["src/shared/UserService.java"],
            )

            manager.ensure_layout()
            manager.acquire_write_lock(task_a)

            with pytest.raises(WriteLockConflictError):
                manager.acquire_write_lock(task_b)
