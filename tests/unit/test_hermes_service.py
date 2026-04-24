"""Hermes服务单元测试

测试FastAPI服务核心能力：
- 启动CLI会话API
- SSE事件流格式
- 干预会话API
- 取消会话API
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from io import StringIO
import subprocess


class TestStartSessionApi:
    """启动会话API测试"""

    def test_start_session_returns_session_id(self):
        """测试：启动API返回session_id"""
        from claudeflow.hermes_service import app, driver
        from fastapi.testclient import TestClient

        # Mock driver
        mock_process = Mock()
        mock_process.poll.return_value = None

        with patch.object(driver, 'start_session', return_value=(mock_process, "session-abc-123")):
            client = TestClient(app)

            response = client.post(
                "/api/session/start",
                json={"prompt": "创建一个Python模块hello.py"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert data["session_id"] == "session-abc-123"
            assert data["status"] == "running"

    def test_start_session_empty_prompt_returns_422(self):
        """测试：空prompt返回422验证错误"""
        from claudeflow.hermes_service import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.post(
            "/api/session/start",
            json={"prompt": ""}
        )

        # FastAPI/Pydantic使用422表示验证错误
        assert response.status_code == 422

    def test_start_session_missing_prompt_returns_422(self):
        """测试：缺少prompt返回422验证错误"""
        from claudeflow.hermes_service import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        response = client.post(
            "/api/session/start",
            json={}
        )

        # FastAPI/Pydantic使用422表示验证错误
        assert response.status_code == 422


class TestEventsStreamApi:
    """SSE事件流API测试"""

    def test_events_stream_sse_format(self):
        """测试：事件流SSE格式正确"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"

        # 模拟事件输出
        events_output = [
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Glob"}]}}\n',
            '{"type":"assistant","message":{"content":[{"type":"text","text":"找到5个文件"}]}}\n',
            '{"type":"result","subtype":"success","result":"任务完成"}\n'
        ]
        mock_process = Mock()
        mock_process.stdout = StringIO(''.join(events_output))

        mock_session = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        with patch.object(driver, 'get_session', return_value=mock_session):
            with patch.object(driver, 'monitor_events') as mock_monitor:
                # 返回解析后的事件列表
                mock_monitor.return_value = iter([
                    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Glob"}]}},
                    {"type": "assistant", "message": {"content": [{"type": "text", "text": "找到5个文件"}]}},
                    {"type": "result", "subtype": "success", "result": "任务完成"}
                ])

                client = TestClient(app)

                response = client.get(f"/api/session/{session_id}/events")

                assert response.status_code == 200
                # SSE格式验证
                content = response.text
                assert "data:" in content
                # 验证JSON格式
                lines = content.strip().split("\n\n")
                for line in lines:
                    if line.startswith("data:"):
                        json_str = line.replace("data: ", "")
                        event = json.loads(json_str)
                        assert "type" in event

    def test_events_stream_session_not_found(self):
        """测试：session不存在返回404"""
        from claudeflow.hermes_service import app, driver
        from fastapi.testclient import TestClient

        with patch.object(driver, 'get_session', return_value=None):
            client = TestClient(app)

            response = client.get("/api/session/nonexistent/events")

            assert response.status_code == 404


class TestRuntimeApi:
    """Runtime API 测试"""

    def test_runtime_status_returns_payload(self):
        from claudeflow.hermes_service import app, runtime_manager
        from fastapi.testclient import TestClient

        with patch.object(
            runtime_manager,
            "get_runtime_status",
            return_value={
                "repo_path": "/tmp/repo",
                "active_agents": 2,
                "queued_tasks": 3,
                "completed_tasks": 4,
                "failed_tasks": 1,
                "intervention_required": True,
                "running_tasks": ["task_a", "task_b"],
            },
        ):
            client = TestClient(app)
            response = client.get("/api/runtime/status")

            assert response.status_code == 200
            assert response.json()["active_agents"] == 2

    def test_runtime_sessions_returns_payload(self):
        from claudeflow.hermes_service import app, runtime_manager
        from fastapi.testclient import TestClient

        with patch.object(
            runtime_manager,
            "list_session_indexes",
            return_value=[
                {
                    "task_id": "task_a",
                    "session_id": "sess-a",
                    "status": "running",
                    "priority": "high",
                }
            ],
        ):
            client = TestClient(app)
            response = client.get("/api/runtime/sessions")

            assert response.status_code == 200
            assert response.json()["sessions"][0]["task_id"] == "task_a"

    def test_runtime_plan_returns_payload(self):
        from claudeflow.hermes_service import app, runtime_manager
        from fastapi.testclient import TestClient

        with patch.object(
            runtime_manager,
            "get_dispatch_plan",
            return_value={
                "runnable": [],
                "blocked": [{"task_id": "task_b", "priority": "medium", "reason_code": "waiting_dependency", "reason": "等待依赖完成"}],
                "running": [{"task_id": "task_a", "priority": "high", "reason_code": "session_running", "reason": "任务已有运行中的会话"}],
            },
        ):
            client = TestClient(app)
            response = client.get("/api/runtime/plan")

            assert response.status_code == 200
            data = response.json()
            assert data["blocked"][0]["reason_code"] == "waiting_dependency"
            assert data["running"][0]["task_id"] == "task_a"

    def test_runtime_explain_returns_404_for_unknown_task(self):
        from claudeflow.hermes_service import app, runtime_manager
        from claudeflow.runtime import UnknownTaskError
        from fastapi.testclient import TestClient

        with patch.object(runtime_manager, "explain_task", side_effect=UnknownTaskError("task graph 中不存在任务: missing")):
            client = TestClient(app)
            response = client.get("/api/runtime/explain/missing")

            assert response.status_code == 404

    def test_runtime_dispatch_returns_result(self):
        from claudeflow.hermes_service import app, runtime_manager
        from fastapi.testclient import TestClient

        with patch.object(
            runtime_manager,
            "dispatch_runnable_tasks",
            return_value={
                "runnable_count": 1,
                "blocked_count": 0,
                "active_agents": 0,
                "available_slots": 1,
                "max_concurrent": 2,
                "started": [{"task_id": "task_a", "session_id": "sess-a", "priority": "high"}],
                "skipped": [],
                "blocked": [],
            },
        ) as mock_dispatch:
            client = TestClient(app)
            response = client.post("/api/runtime/dispatch", json={"max_concurrent": 2})

            assert response.status_code == 200
            data = response.json()
            assert data["started"][0]["task_id"] == "task_a"
            mock_dispatch.assert_called_once_with(base_branch="HEAD", limit=None, max_concurrent=2)

    def test_runtime_complete_returns_updated_task(self):
        from claudeflow.hermes_service import app, runtime_manager
        from fastapi.testclient import TestClient

        with patch.object(
            runtime_manager,
            "complete_worker",
            return_value={
                "task_id": "task_a",
                "status": "completed",
                "summary": "done",
            },
        ) as mock_complete:
            client = TestClient(app)
            response = client.post(
                "/api/runtime/task/task_a/complete",
                json={"summary": "done", "changed_files": ["a.py"], "test_status": "passed", "test_count": 2},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "completed"
            mock_complete.assert_called_once_with(
                "task_a",
                summary="done",
                changed_files=["a.py"],
                tests={"status": "passed", "count": 2},
            )

    def test_runtime_fail_returns_updated_task(self):
        from claudeflow.hermes_service import app, runtime_manager
        from fastapi.testclient import TestClient

        with patch.object(
            runtime_manager,
            "fail_worker",
            return_value={
                "task_id": "task_a",
                "status": "failed",
                "summary": "blocked",
            },
        ) as mock_fail:
            client = TestClient(app)
            response = client.post(
                "/api/runtime/task/task_a/fail",
                json={"reason": "blocked"},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "failed"
            mock_fail.assert_called_once_with("task_a", "blocked")


class TestInterveneApi:
    """干预会话API测试"""

    def test_intervene_success(self):
        """测试：干预API返回正确响应"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"

        # 预存session
        mock_process = Mock()
        mock_session = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="原始任务"
        )

        # 干预返回新进程
        new_process = Mock()

        with patch.object(driver, 'get_session', return_value=mock_session):
            with patch.object(driver, 'intervene', return_value=new_process):
                client = TestClient(app)

                response = client.post(
                    f"/api/session/{session_id}/intervene",
                    json={"prompt": "请修改代码"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] == session_id
                assert data["status"] == "intervened"

    def test_intervene_session_not_found(self):
        """测试：干预不存在的session返回404"""
        from claudeflow.hermes_service import app, driver
        from fastapi.testclient import TestClient

        with patch.object(driver, 'get_session', return_value=None):
            client = TestClient(app)

            response = client.post(
                "/api/session/nonexistent/intervene",
                json={"prompt": "继续"}
            )

            assert response.status_code == 404

    def test_intervene_empty_prompt_returns_422(self):
        """测试：空干预prompt返回422验证错误"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"
        mock_session = CliSession(
            session_id=session_id,
            process=Mock(),
            prompt="test"
        )

        with patch.object(driver, 'get_session', return_value=mock_session):
            client = TestClient(app)

            response = client.post(
                f"/api/session/{session_id}/intervene",
                json={"prompt": ""}
            )

        # FastAPI/Pydantic使用422表示验证错误
        assert response.status_code == 422


class TestCancelApi:
    """取消会话API测试"""

    def test_cancel_terminates_session(self):
        """测试：取消API终止会话"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"

        mock_process = Mock()
        mock_process.poll.return_value = None  # 进程运行中

        mock_session = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        with patch.object(driver, 'get_session', return_value=mock_session):
            with patch.object(driver, 'clear_session') as mock_clear:
                client = TestClient(app)

                response = client.post(f"/api/session/{session_id}/cancel")

                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] == session_id
                assert data["status"] == "cancelled"
                # 验证clear_session被调用
                mock_clear.assert_called_once_with(session_id)

    def test_cancel_nonexistent_session(self):
        """测试：取消不存在的session返回200（已不存在）"""
        from claudeflow.hermes_service import app, driver
        from fastapi.testclient import TestClient

        with patch.object(driver, 'get_session', return_value=None):
            with patch.object(driver, 'clear_session') as mock_clear:
                client = TestClient(app)

                response = client.post("/api/session/nonexistent/cancel")

                # 即使不存在也返回成功
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "cancelled"


class TestStatusApi:
    """状态查询API测试"""

    def test_status_running(self):
        """测试：查询运行中状态"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"

        mock_process = Mock()
        mock_process.poll.return_value = None  # 运行中

        mock_session = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test",
            events=[]
        )

        with patch.object(driver, 'get_session', return_value=mock_session):
            with patch.object(driver, 'is_process_alive', return_value=True):
                client = TestClient(app)

                response = client.get(f"/api/session/{session_id}/status")

                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] == session_id
                assert data["status"] == "running"

    def test_status_completed(self):
        """测试：查询已完成状态"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"

        mock_process = Mock()
        mock_process.poll.return_value = 0  # 已结束

        mock_session = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test",
            events=[{"type": "result", "subtype": "success"}]
        )

        with patch.object(driver, 'get_session', return_value=mock_session):
            with patch.object(driver, 'is_process_alive', return_value=False):
                client = TestClient(app)

                response = client.get(f"/api/session/{session_id}/status")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"

    def test_status_not_found(self):
        """测试：查询不存在的session返回404"""
        from claudeflow.hermes_service import app, driver
        from fastapi.testclient import TestClient

        with patch.object(driver, 'get_session', return_value=None):
            client = TestClient(app)

            response = client.get("/api/session/nonexistent/status")

            assert response.status_code == 404


class TestHermesServiceEdgeCases:
    """边界情况测试"""

    def test_start_session_driver_failure(self):
        """测试：driver启动失败返回500"""
        from claudeflow.hermes_service import app, driver
        from fastapi.testclient import TestClient

        with patch.object(driver, 'start_session', side_effect=Exception("CLI启动失败")):
            client = TestClient(app)

            response = client.post(
                "/api/session/start",
                json={"prompt": "测试任务"}
            )

            assert response.status_code == 500

    def test_intervene_driver_failure(self):
        """测试：driver干预失败返回500"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"
        mock_session = CliSession(
            session_id=session_id,
            process=Mock(),
            prompt="test"
        )

        with patch.object(driver, 'get_session', return_value=mock_session):
            with patch.object(driver, 'intervene', side_effect=ValueError("session_id无效")):
                client = TestClient(app)

                response = client.post(
                    f"/api/session/{session_id}/intervene",
                    json={"prompt": "继续"}
                )

                assert response.status_code == 500

    def test_events_stream_with_error_event(self):
        """测试：事件流包含错误事件"""
        from claudeflow.hermes_service import app, driver
        from claudeflow.cli_driver import CliSession
        from fastapi.testclient import TestClient

        session_id = "session-abc-123"

        mock_process = Mock()
        mock_session = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        with patch.object(driver, 'get_session', return_value=mock_session):
            with patch.object(driver, 'monitor_events') as mock_monitor:
                # 包含错误事件
                mock_monitor.return_value = iter([
                    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Glob"}]}},
                    {"type": "result", "subtype": "error", "error": "执行失败"}
                ])

                client = TestClient(app)

                response = client.get(f"/api/session/{session_id}/events")

                assert response.status_code == 200
                content = response.text
                # 错误事件也应该出现在流中
                assert "error" in content
