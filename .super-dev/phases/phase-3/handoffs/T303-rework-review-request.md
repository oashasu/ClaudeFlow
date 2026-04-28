# T303 Rework Review Request

## Task Summary

**T303**: 固化 runtime schema/sample 并接入前端 parse validate

## Rework Context

Codex governor review 结论为 `rework_required`，阻断点：

> `status / sessions / events` live payload 仍然绕过 parse/validate 主链

## Rework Changes

### 1. parse/validate 接入 live 读取链

| 文件 | 变更 |
|------|------|
| `console/src/composables/useRuntimeLiveData.ts` | loadLiveStatus 接入 parseStatus/parseSessions |
| `console/src/composables/useRuntimeLiveData.ts` | loadLiveSessionEvents 接入 parseSessionEvents |

**关键代码**:
```typescript
// loadLiveStatus
const statusResult = runtimeValidator.parseStatus(JSON.stringify(statusPayload))
if (statusResult.error) {
  state.value.parseError = `Runtime Status 协议校验失败: ${statusResult.error}`
  state.value.status = null
  state.value.sessions = []
  return
}
state.value.status = statusResult.data

const sessionsPayload = await runtimeApi.sessions()
const sessionsResult = runtimeValidator.parseSessions(JSON.stringify(sessionsPayload.sessions))
if (sessionsResult.error) {
  state.value.parseError = `Runtime Sessions 协议校验失败: ${sessionsResult.error}`
  state.value.status = null
  state.value.sessions = []
  return
}
state.value.sessions = sessionsResult.data ?? []

// loadLiveSessionEvents
const eventsResult = runtimeValidator.parseSessionEvents(JSON.stringify(payload))
if (eventsResult.error) {
  state.value.sessionEventsError = `Session Events 协议校验失败: ${eventsResult.error}`
  state.value.sessionEvents = []
  return
}
state.value.sessionEvents = eventsResult.data?.parsed_events ?? []
```

### 2. 校验失败时清除 state 字段

修复：当校验失败时，设置 `status = null` / `sessions = []`，避免残留初始 sample 值导致测试断言失败。

### 3. 新增测试文件

| 文件 | 说明 |
|------|------|
| `console/tests/runtimeLiveDataValidation.spec.ts` | 6 个测试覆盖 live payload 校验 |

## Test Results

### Frontend Tests
```
console vitest: 68 passed
- runtimeValidator.spec.ts: 21 tests
- runtimeLiveDataValidation.spec.ts: 6 tests (新增)
- 其他测试: 41 tests
```

### Backend Tests
```
tests/unit/test_runtime_schema.py: 20 passed
```

## Acceptance Criteria

### A34: Runtime 协议校验闭环

| 验收项 | 状态 | 证据 |
|--------|------|------|
| status schema/sample | ✅ | runtime-status.schema.json/sample.json |
| sessions schema/sample | ✅ | runtime-sessions.schema.json/sample.json |
| events schema/sample | ✅ | runtime-events.schema.json/sample.json |
| validator 校验增强 | ✅ | runtimeValidator.spec.ts (21 tests) |
| parse 失败显示结构化错误 | ✅ | RuntimeConsole.vue parseError banner |
| live payload 必经 parse | ✅ | runtimeLiveDataValidation.spec.ts (6 tests) |
| 校验失败清除 state | ✅ | 测试断言 status/sessions 为 null/[] |

## Rework Checklist

- [x] parseStatus 接入 loadLiveStatus
- [x] parseSessions 接入 loadLiveStatus
- [x] parseSessionEvents 接入 loadLiveSessionEvents
- [x] 校验失败时设置 parseError/sessionEventsError
- [x] 校验失败时清除 status/sessions/sessionEvents
- [x] 新增 live payload 校验测试
- [x] 所有测试通过 (68 passed)

## Handoff To

**宿主**: Codex
**模式**: governor
**操作**: `/super-dev-review T303`

---
Generated: 2026-04-27T13:55:00Z