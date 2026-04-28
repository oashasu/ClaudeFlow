#!/usr/bin/env python3
"""
runtime_smoke.py - T404: Runtime API 最小主链 Smoke 入口

覆盖 A44 要求：
- /api/runtime/status - 运行时总览
- /api/runtime/sessions - session 列表
- /api/session/{session_id}/events-list - session 事件（必选）
- /api/runtime/plan - 调度计划（额外验证）
- /api/runtime/dispatch - dispatch 端点（explain|dispatch 之一）
- /api/runtime/action-audit - 审计记录（action result|audit 之一）
- /health - 健康检查（额外验证）

使用 FastAPI TestClient 进行端点验证，不依赖真实 CLI 进程。

执行方式：
    PYTHONPATH=src python3 scripts/runtime_smoke.py

返回：
    成功：输出每个端点的验证结果，exit code 0
    失败：输出失败端点和错误信息，exit code 1
"""

import sys
import os

# 确保 src 在 PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi.testclient import TestClient
from claudeflow.runtime.api import app, runtime_manager, driver, audit_store
from claudeflow.runtime.action_audit import create_audit_record


def smoke_test():
    """执行 runtime API smoke 测试"""
    client = TestClient(app)
    results = []

    print("=" * 60)
    print("Runtime API Smoke Test - A44")
    print("=" * 60)

    # 1. Status 端点
    print("\n[1] GET /api/runtime/status")
    try:
        resp = client.get("/api/runtime/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "repo_path" in data
        assert "active_agents" in data
        assert "intervention_required" in data
        print(f"   repo_path: {data['repo_path']}")
        print(f"   active_agents: {data['active_agents']}")
        results.append(("status", "PASS"))
    except Exception as e:
        print(f"   FAIL: {e}")
        results.append(("status", "FAIL", str(e)))

    # 2. Sessions 端点
    print("\n[2] GET /api/runtime/sessions")
    try:
        resp = client.get("/api/runtime/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        print(f"   sessions count: {len(data['sessions'])}")
        results.append(("sessions", "PASS"))
    except Exception as e:
        print(f"   FAIL: {e}")
        results.append(("sessions", "FAIL", str(e)))

    # 3. Events 端点（必须先创建测试 session 以验证真实响应）
    print("\n[3] GET /api/session/{session_id}/events-list")
    try:
        # 创建一个 mock session 以验证 events 端点响应结构
        test_session_id = "smoke_test_session"
        from unittest.mock import MagicMock
        from claudeflow.runtime.cli_driver import CliSession

        mock_process = MagicMock()
        mock_process.poll.return_value = None  # process is alive

        mock_session = CliSession(
            session_id=test_session_id,
            process=mock_process,
            prompt="smoke test prompt",
            events=[
                {"type": "assistant", "content": "test event 1"},
                {"type": "result", "content": "test result"},
            ]
        )
        driver.sessions[test_session_id] = mock_session

        resp = client.get(f"/api/session/{test_session_id}/events-list")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert "events_count" in data
        assert "parsed_events" in data
        assert "raw_events" in data
        print(f"   session_id: {data['session_id']}")
        print(f"   events_count: {data['events_count']}")

        # 清理 mock session
        driver.sessions.pop(test_session_id, None)
        results.append(("events-list", "PASS"))
    except Exception as e:
        print(f"   FAIL: {e}")
        results.append(("events-list", "FAIL", str(e)))

    # 4. Plan 端点（A44 额外验证）
    print("\n[4] GET /api/runtime/plan")
    try:
        resp = client.get("/api/runtime/plan?executor_type=claude")
        assert resp.status_code == 200
        data = resp.json()
        assert "runnable" in data
        assert "blocked" in data
        assert "running" in data
        print(f"   runnable: {len(data['runnable'])} tasks")
        print(f"   blocked: {len(data['blocked'])} tasks")
        results.append(("plan", "PASS"))
    except Exception as e:
        print(f"   FAIL: {e}")
        results.append(("plan", "FAIL", str(e)))

    # 5. Dispatch 端点（explain 或 dispatch，选择 dispatch）
    print("\n[5] POST /api/runtime/dispatch")
    try:
        resp = client.post(
            "/api/runtime/dispatch",
            json={"base_branch": "HEAD", "max_concurrent": 1, "executor_type": "claude"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "runnable_count" in data
        assert "active_agents" in data
        assert "started" in data
        print(f"   runnable_count: {data['runnable_count']}")
        print(f"   started: {len(data['started'])} tasks")
        results.append(("dispatch", "PASS"))
    except Exception as e:
        print(f"   FAIL: {e}")
        results.append(("dispatch", "FAIL", str(e)))

    # 6. Action Audit 端点（action result 或 audit，选择 audit）
    # 先写入一条测试记录确保有数据
    print("\n[6] GET /api/runtime/action-audit")
    try:
        # 写入一条测试审计记录
        test_record = create_audit_record(
            action_type="smoke_test",
            target_task_id="smoke_task",
            target_session_id="smoke_session",
            success=True,
            message="Smoke test audit record",
        )
        audit_store.write_record(test_record)

        resp = client.get("/api/runtime/action-audit?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "records" in data
        assert "total" in data
        print(f"   records: {data['total']} audit entries")
        # 验证刚写入的记录存在
        smoke_records = [r for r in data["records"] if r["action_type"] == "smoke_test"]
        assert len(smoke_records) >= 1, "smoke_test audit record not found"
        print(f"   smoke_test record found: {smoke_records[0]['action_id']}")
        results.append(("action-audit", "PASS"))
    except Exception as e:
        print(f"   FAIL: {e}")
        results.append(("action-audit", "FAIL", str(e)))

    # 7. Health 端点（额外验证）
    print("\n[7] GET /health")
    try:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        print(f"   status: {data['status']}")
        print(f"   version: {data['version']}")
        results.append(("health", "PASS"))
    except Exception as e:
        print(f"   FAIL: {e}")
        results.append(("health", "FAIL", str(e)))

    # 汇总结果
    print("\n" + "=" * 60)
    print("Smoke Test Summary")
    print("=" * 60)

    passed = sum(1 for r in results if r[1] == "PASS")
    failed = sum(1 for r in results if r[1] == "FAIL")

    for name, status, *extra in results:
        if status == "PASS":
            print(f"  [{status}] {name}")
        else:
            print(f"  [{status}] {name} - {extra[0] if extra else 'unknown error'}")

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed > 0:
        print("\nSmoke test FAILED")
        return 1
    else:
        print("\nSmoke test PASSED")
        return 0


if __name__ == "__main__":
    exit_code = smoke_test()
    sys.exit(exit_code)