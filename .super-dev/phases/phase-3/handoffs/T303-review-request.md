# T303 Review Request

## Task Summary

**T303**: 固化 runtime schema/sample 并接入前端 parse validate

## Implementation Files

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `examples/runtime-status.schema.json` | 新建 | RuntimeStatus JSON Schema |
| `examples/runtime-status.sample.json` | 新建 | RuntimeStatus 示例数据 |
| `examples/runtime-sessions.schema.json` | 新建 | RuntimeSession[] JSON Schema |
| `examples/runtime-sessions.sample.json` | 新建 | RuntimeSession[] 示例数据 |
| `examples/runtime-events.schema.json` | 新建 | RuntimeSessionEvents JSON Schema |
| `examples/runtime-events.sample.json` | 新建 | RuntimeSessionEvents 示例数据 |
| `console/src/validators/runtime.ts` | 修改 | 增强字段校验覆盖所有关键字段 |
| `console/tests/runtimeValidator.spec.ts` | 新建 | 前端 validator 测试（21 tests） |
| `tests/unit/test_runtime_schema.py` | 新建 | 后端 schema 验证测试（20 tests） |

## Acceptance Criteria

### A34: Runtime 协议校验闭环

| 验收项 | 状态 | 验证方式 |
|--------|------|---------|
| status schema/sample | ✅ | runtime-status.schema.json/sample.json |
| sessions schema/sample | ✅ | runtime-sessions.schema.json/sample.json |
| events schema/sample | ✅ | runtime-events.schema.json/sample.json |
| validator 校验增强 | ✅ | runtimeValidator.spec.ts (21 tests) |
| parse 失败显示结构化错误 | ✅ | RuntimeConsole.vue 第 97-104 行 parseError banner |
| schema 验证测试 | ✅ | test_runtime_schema.py (20 tests) |

## Test Results

### Frontend Tests
```
console vitest: 62 passed (含 21 validator tests)
```

### Backend Tests
```
tests/unit/test_runtime_schema.py: 20 passed
```

## Key Implementation Details

### 1. Schema 文件覆盖
原有 schema：plan, dispatch, explain
新增 schema：status, sessions, events

### 2. Validator 校验增强
```typescript
// 增强字段校验示例
function isStatus(obj: unknown): boolean {
  if (typeof obj !== 'object' || obj === null) return false
  const s = obj as Record<string, unknown>
  if (typeof s.repo_path !== 'string' || typeof s.active_agents !== 'number') return false
  if (typeof s.queued_tasks !== 'number' || typeof s.completed_tasks !== 'number') return false
  if (typeof s.failed_tasks !== 'number' || typeof s.intervention_required !== 'boolean') return false
  if (!Array.isArray(s.running_tasks)) return false
  return true
}
```

### 3. Parse 失败显示
RuntimeConsole.vue 第 97-104 行：
```vue
<div v-if="liveData.state.value.parseError" class="error-banner parse">
  <AlertTriangle :size="16" />
  {{ liveData.state.value.parseError }}
</div>
```

### 4. Schema 与 Sample 文件结构
- 使用 JSON Schema draft 2020-12 格式
- required 字段定义所有关键属性
- enum 约束枚举值（如 status, priority, event type）

## Review Checklist

- [ ] 所有 schema 文件格式正确
- [ ] sample 文件与 schema 匹配
- [ ] validator 校验覆盖所有关键字段
- [ ] parse 失败时前端显示结构化错误
- [ ] 测试覆盖率达标
- [ ] 无硬编码敏感数据
- [ ] 错误处理完整

## Handoff To

**宿主**: Codex
**模式**: governor
**操作**: `/super-dev-review T303`

---
Generated: 2026-04-27T13:45:00Z