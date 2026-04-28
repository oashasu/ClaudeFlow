"""Tests for runtime/api.py - the replacement for hermes_service.py."""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from claudeflow.runtime.api import app
    return TestClient(app)


@pytest.fixture
def mock_driver():
    with patch("claudeflow.runtime.api.driver") as driver:
        yield driver


@pytest.fixture
def mock_runtime_manager():
    with patch("claudeflow.runtime.api.runtime_manager") as rm:
        yield rm


# ── Health ──────────────────────────────────────────────────


class TestHealth:

    def test_health_returns_healthy(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "3.0.0"


# ── Session 端点 ────────────────────────────────────────────


class TestSessionStart:

    def test_start_session_success(self, client, mock_driver):
        mock_driver.start_session.return_value = (MagicMock(), "sess-001")
        resp = client.post("/api/session/start", json={"prompt": "do something"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-001"
        assert data["status"] == "running"

    def test_start_session_no_session_id(self, client, mock_driver):
        mock_driver.start_session.return_value = (MagicMock(), None)
        resp = client.post("/api/session/start", json={"prompt": "do something"})
        assert resp.status_code == 500

    def test_start_session_cli_failure(self, client, mock_driver):
        mock_driver.start_session.side_effect = RuntimeError("CLI crashed")
        resp = client.post("/api/session/start", json={"prompt": "do something"})
        assert resp.status_code == 500

    def test_start_session_empty_prompt(self, client, mock_driver):
        resp = client.post("/api/session/start", json={"prompt": ""})
        assert resp.status_code == 422


class TestSessionStatus:

    def test_status_running(self, client, mock_driver):
        mock_session = MagicMock()
        mock_session.events = [{"type": "assistant"}]
        mock_driver.get_session.return_value = mock_session
        mock_driver.is_process_alive.return_value = True

        resp = client.get("/api/session/sess-001/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-001"
        assert data["status"] == "running"
        assert data["events_count"] == 1

    def test_status_completed(self, client, mock_driver):
        mock_session = MagicMock()
        mock_session.events = [{"type": "result"}]
        mock_driver.get_session.return_value = mock_session
        mock_driver.is_process_alive.return_value = False

        resp = client.get("/api/session/sess-001/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_status_not_found(self, client, mock_driver):
        mock_driver.get_session.return_value = None
        resp = client.get("/api/session/nonexistent/status")
        assert resp.status_code == 404


class TestSessionEventsList:

    def test_events_list(self, client, mock_driver):
        mock_session = MagicMock()
        mock_session.events = [{"type": "assistant", "content": {"type": "text", "text": "hello"}}]
        mock_driver.get_session.return_value = mock_session
        mock_driver.parse_all_assistant_content.return_value = [
            {"type": "text", "text": "hello"}
        ]

        resp = client.get("/api/session/sess-001/events-list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-001"
        assert data["events_count"] == 1
        assert len(data["parsed_events"]) == 1

    def test_events_list_not_found(self, client, mock_driver):
        mock_driver.get_session.return_value = None
        resp = client.get("/api/session/nonexistent/events-list")
        assert resp.status_code == 404


class TestSessionIntervene:

    def test_intervene_success(self, client, mock_driver):
        mock_driver.get_session.return_value = MagicMock()
        mock_driver.intervene.return_value = None

        resp = client.post("/api/session/sess-001/intervene", json={"prompt": "check quality"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-001"
        assert data["status"] == "intervened"

    def test_intervene_session_not_found(self, client, mock_driver):
        mock_driver.get_session.return_value = None
        resp = client.post("/api/session/nonexistent/intervene", json={"prompt": "test"})
        assert resp.status_code == 404

    def test_intervene_cli_error(self, client, mock_driver):
        mock_driver.get_session.return_value = MagicMock()
        mock_driver.intervene.side_effect = ValueError("No process")
        resp = client.post("/api/session/sess-001/intervene", json={"prompt": "test"})
        assert resp.status_code == 500


class TestSessionCancel:

    def test_cancel_success(self, client, mock_driver):
        mock_driver.clear_session.return_value = None
        resp = client.post("/api/session/sess-001/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"


# ── Runtime 端点 ────────────────────────────────────────────


class TestRuntimeStatus:

    def test_runtime_status(self, client, mock_runtime_manager):
        mock_runtime_manager.get_runtime_status.return_value = {
            "repo_path": "/tmp/repo",
            "active_agents": 1,
            "queued_tasks": 2,
            "completed_tasks": 3,
            "failed_tasks": 0,
            "intervention_required": False,
            "running_tasks": ["task-1"],
        }
        resp = client.get("/api/runtime/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_agents"] == 1
        assert data["running_tasks"] == ["task-1"]


class TestRuntimePlan:

    def test_runtime_plan(self, client, mock_runtime_manager):
        mock_task = MagicMock()
        mock_task.task_id = "task-1"
        mock_task.priority = "high"
        mock_task.executor_type = "claude"  # T106: 宿主字段
        mock_task.phase_id = "phase-1"  # T109: RuntimeTaskSpec 字段

        mock_runtime_manager.get_dispatch_plan.return_value = {
            "runnable": [mock_task],
            "blocked": [],
            "running": [],
        }

        resp = client.get("/api/runtime/plan")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runnable"]) == 1
        assert data["runnable"][0]["task_id"] == "task-1"
        assert data["runnable"][0]["executor_type"] == "claude"  # T106: 验证宿主字段
        assert data["runnable"][0]["phase_id"] == "phase-1"  # T109: 验证 RuntimeTaskSpec 字段

    def test_runtime_plan_with_executor_type_param(self, client, mock_runtime_manager):
        """T106: 测试 executor_type 参数传递"""
        mock_task = MagicMock()
        mock_task.task_id = "task-1"
        mock_task.priority = "high"
        mock_task.executor_type = "codex"
        mock_task.phase_id = "phase-1"

        mock_runtime_manager.get_dispatch_plan.return_value = {
            "runnable": [mock_task],
            "blocked": [],
            "running": [],
        }

        resp = client.get("/api/runtime/plan?executor_type=codex")
        assert resp.status_code == 200
        mock_runtime_manager.get_dispatch_plan.assert_called_with(executor_type="codex")


class TestRuntimeSessions:

    def test_runtime_sessions(self, client, mock_runtime_manager):
        mock_runtime_manager.list_session_indexes.return_value = [
            {"task_id": "task-1", "session_id": "sess-001", "status": "running", "priority": "high"}
        ]
        resp = client.get("/api/runtime/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sessions"]) == 1


class TestRuntimeExplain:

    def test_explain_success(self, client, mock_runtime_manager):
        mock_runtime_manager.explain_task.return_value = {
            "task_id": "task-1",
            "state": "blocked",
            "priority": "medium",
            "reason_code": "waiting_dependency",
            "reason": "Waiting for task-0",
            "dependencies": ["task-0"],
        }
        resp = client.get("/api/runtime/explain/task-1")
        assert resp.status_code == 200
        assert resp.json()["state"] == "blocked"

    def test_explain_not_found(self, client, mock_runtime_manager):
        from claudeflow.runtime.manager import UnknownTaskError
        mock_runtime_manager.explain_task.side_effect = UnknownTaskError("task-x")
        resp = client.get("/api/runtime/explain/task-x")
        assert resp.status_code == 404


class TestRuntimeDispatch:

    def test_dispatch(self, client, mock_runtime_manager):
        mock_runtime_manager.dispatch_runnable_tasks.return_value = {
            "runnable_count": 1,
            "blocked_count": 0,
            "active_agents": 1,
            "available_slots": 1,
            "max_concurrent": None,
            "started": [],
            "skipped": [],
            "blocked": [],
        }
        resp = client.post("/api/runtime/dispatch", json={"base_branch": "HEAD"})
        assert resp.status_code == 200
        assert resp.json()["runnable_count"] == 1

    def test_dispatch_with_executor_type(self, client, mock_runtime_manager):
        """T106: 测试 executor_type 参数传递到 dispatch"""
        mock_runtime_manager.dispatch_runnable_tasks.return_value = {
            "runnable_count": 1,
            "blocked_count": 0,
            "active_agents": 1,
            "available_slots": 1,
            "max_concurrent": None,
            "started": [],
            "skipped": [],
            "blocked": [],
        }
        resp = client.post("/api/runtime/dispatch", json={
            "base_branch": "HEAD",
            "executor_type": "codex"
        })
        assert resp.status_code == 200
        mock_runtime_manager.dispatch_runnable_tasks.assert_called_with(
            base_branch="HEAD",
            limit=None,
            max_concurrent=None,
            executor_type="codex"
        )


class TestRuntimeGovernanceDispatch:

    def test_governance_dispatch_success(self, client, mock_runtime_manager):
        """T106: 测试治理入口派发成功"""
        mock_runtime_manager.dispatch_from_governance.return_value = {
            "runnable_count": 2,
            "blocked_count": 1,
            "started": ["T106", "T107"],
            "skipped": [],
            "blocked": ["T108"],
        }
        resp = client.post("/api/runtime/dispatch/governance", json={
            "governance_root": ".super-dev",
            "phase_id": "phase-1",
            "base_branch": "HEAD"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["runnable_count"] == 2
        mock_runtime_manager.dispatch_from_governance.assert_called_with(
            governance_root=".super-dev",
            phase_id="phase-1",
            base_branch="HEAD",
            limit=None
        )

    def test_governance_dispatch_with_limit(self, client, mock_runtime_manager):
        """T106: 测试治理入口派发带 limit 参数"""
        mock_runtime_manager.dispatch_from_governance.return_value = {
            "runnable_count": 1,
            "blocked_count": 0,
            "started": ["T106"],
            "skipped": [],
            "blocked": [],
        }
        resp = client.post("/api/runtime/dispatch/governance", json={
            "governance_root": ".super-dev",
            "phase_id": "phase-1",
            "base_branch": "HEAD",
            "limit": 1
        })
        assert resp.status_code == 200
        mock_runtime_manager.dispatch_from_governance.assert_called_with(
            governance_root=".super-dev",
            phase_id="phase-1",
            base_branch="HEAD",
            limit=1
        )

    def test_governance_dispatch_missing_params(self, client, mock_runtime_manager):
        """T106: 测试治理入口缺少必需参数"""
        resp = client.post("/api/runtime/dispatch/governance", json={
            "governance_root": ".super-dev"
        })
        assert resp.status_code == 422  # Validation error


class TestRuntimeComplete:

    def test_complete_success(self, client, mock_runtime_manager):
        mock_runtime_manager.complete_worker.return_value = {
            "task_id": "task-1",
            "status": "completed",
        }
        resp = client.post(
            "/api/runtime/task/task-1/complete",
            json={"summary": "done", "changed_files": ["a.py"]},
        )
        assert resp.status_code == 200

    def test_complete_not_found(self, client, mock_runtime_manager):
        from claudeflow.runtime.manager import UnknownTaskError
        mock_runtime_manager.complete_worker.side_effect = UnknownTaskError("task-x")
        resp = client.post("/api/runtime/task/task-x/complete", json={"summary": "done"})
        assert resp.status_code == 404


class TestRuntimeFail:

    def test_fail_success(self, client, mock_runtime_manager):
        mock_runtime_manager.fail_worker.return_value = {
            "task_id": "task-1",
            "status": "failed",
        }
        resp = client.post(
            "/api/runtime/task/task-1/fail",
            json={"reason": "timeout"},
        )
        assert resp.status_code == 200

    def test_fail_not_found(self, client, mock_runtime_manager):
        from claudeflow.runtime.manager import UnknownTaskError
        mock_runtime_manager.fail_worker.side_effect = UnknownTaskError("task-x")
        resp = client.post("/api/runtime/task/task-x/fail", json={"reason": "err"})
        assert resp.status_code == 404


class TestRouteRegistration:

    def test_all_expected_routes_registered(self):
        from claudeflow.runtime.api import app
        routes = [route.path for route in app.routes]

        expected = [
            "/health",
            "/api/session/start",
            "/api/session/{session_id}/events",
            "/api/session/{session_id}/intervene",
            "/api/session/{session_id}/cancel",
            "/api/session/{session_id}/status",
            "/api/session/{session_id}/events-list",
            "/api/runtime/plan",
            "/api/runtime/status",
            "/api/runtime/sessions",
            "/api/runtime/explain/{task_id}",
            "/api/runtime/dispatch",
            "/api/runtime/dispatch/governance",  # T106: 治理入口
            "/api/runtime/task/{task_id}/complete",
            "/api/runtime/task/{task_id}/fail",
        ]

        for route in expected:
            assert route in routes, f"Missing route: {route}"
