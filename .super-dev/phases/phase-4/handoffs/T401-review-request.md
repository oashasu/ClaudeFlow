# T401 Review Request

## 任务定义
- 目标: 收口 composable/runtime API 相关共享测试 harness 与 mock 基座
- 输出: 统一 setup/mount/mock/flush 入口
- 验收: A42

## 实现内容

### 1. 测试 Harness 文件
`console/tests/helpers/runtimeHarness.ts`:
- `createRuntimeApiMocks()` - unified mock factory
- `withComposable()` - Vue setup context helper for composable testing
- `flushPromises()` - async helper for waiting pending promises
- `captureWarnings()` - console warning capture
- `assertNoLifecycleWarning()` - assertion helper
- Default mock data for all runtime API responses

### 2. 更新测试使用 Harness
- `runtimeLiveDataValidation.spec.ts`: 使用 `withComposable` 避免 lifecycle warning
- `RuntimeConsole.spec.ts`: 正确 mock `listActionAudit` 避免 audit fetch warning

## 测试证据

```bash
npm test -- --run
 Test Files  10 passed (10)
 Tests  68 passed (68)
```

无 Vue lifecycle warning ("onMounted is called when there is no active component instance")
无 audit fetch warning ("Failed to parse URL")

## A42 验收对照

| 条件 | 状态 | 证据 |
|------|------|------|
| composable 测试运行在标准 Vue setup/harness | ✅ | withComposable helper 在 defineComponent setup 内调用 composable |
| runtime API mock 统一基座 | ✅ | createRuntimeApiMocks() factory |
| flush 方式统一 | ✅ | flushPromises() helper |
| mount 方式统一 | ✅ | withComposable + mountRuntimeConsole |

## review_ready
✅ 所有测试通过，无 warnings，harness 已实际使用