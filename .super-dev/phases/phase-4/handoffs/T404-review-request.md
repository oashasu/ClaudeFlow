# T404 Handoff Review Request (Rework Round 1)

## 任务完成摘要

**任务**: T404 - Runtime API 最小主链 Smoke 入口

**验收目标**:
- A44: 真实可运行 smoke 入口，覆盖 status/sessions/events 以及 explain|dispatch、action result|audit 中各一条

## 返工修复内容

### 原问题

Governor review 发现 events 端点缺失：
- A44 明确要求覆盖 status/sessions/events（最小主链）
- 原脚本用 plan 替代 events，不符合验收要求

### 修复方案

在 `scripts/runtime_smoke.py` 添加 events-list 端点测试：
- 创建 mock CliSession 对象验证响应结构
- 使用真实 API 端点 `/api/session/{session_id}/events-list`
- 验证返回字段：session_id, events_count, parsed_events, raw_events

### 端点覆盖（修复后）

| 端点 | 方法 | A44 要求 | 验证内容 |
|------|------|----------|----------|
| `/api/runtime/status` | GET | status ✅ | repo_path, active_agents |
| `/api/runtime/sessions` | GET | sessions ✅ | sessions 数组 |
| `/api/session/{session_id}/events-list` | GET | events ✅ | session_id, events_count, parsed_events, raw_events |
| `/api/runtime/dispatch` | POST | dispatch ✅ | runnable_count, started |
| `/api/runtime/action-audit` | GET | audit ✅ | records 数组 + smoke_test 记录 |
| `/api/runtime/plan` | GET | 额外验证 | runnable/blocked/running |
| `/health` | GET | 额外验证 | status=healthy |

## 验收证据

### A44 验证
```bash
cd /Users/claw/sandbox/personal/claudeflow
PYTHONPATH=src python3 scripts/runtime_smoke.py
```

输出：
```
============================================================
Runtime API Smoke Test - A44
============================================================

[1] GET /api/runtime/status
   repo_path: /Users/claw/sandbox/personal/claudeflow
   active_agents: 6
   [PASS] status

[2] GET /api/runtime/sessions
   sessions count: 6
   [PASS] sessions

[3] GET /api/session/{session_id}/events-list
   session_id: smoke_test_session
   events_count: 2
   [PASS] events-list

[4] GET /api/runtime/plan
   runnable: 0 tasks
   blocked: 0 tasks
   [PASS] plan

[5] POST /api/runtime/dispatch
   runnable_count: 0
   started: 0 tasks
   [PASS] dispatch

[6] GET /api/runtime/action-audit
   records: 10 audit entries
   smoke_test record found: audit-f360c5a4
   [PASS] action-audit

[7] GET /health
   status: healthy
   version: 3.0.0
   [PASS] health

============================================================
Smoke Test Summary
============================================================
Total: 7 passed, 0 failed

Smoke test PASSED
```

## Blocker 检查

无 blocker：
- 真实可运行脚本，exit code 0 ✅
- status/sessions/events 端点覆盖（最小主链）✅
- dispatch 端点覆盖（explain|dispatch 之一）✅
- action-audit 端点覆盖（action result|audit 之一）✅
- events-list 端点使用 mock CliSession 验证真实 API 响应 ✅

## 下一步

请求 governor review T404 rework round 1，确认 A44 验收通过。