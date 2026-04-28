# Runtime Testing & Observability Guide

> 最后更新：2026-04-27
> 适用版本：Runtime V3.1+

本文档说明 Runtime Console 与 Python Runtime API 的测试入口、mock 约定、smoke 入口和排障顺序。

---

## 测试入口总览

| 层级 | 入口 | 命令 | 说明 |
|------|------|------|------|
| 前端单元 | Vitest | `cd console && npm test` | Vue 组件 + composable 测试 |
| Python 单元 | pytest | `PYTHONPATH=src python3 -m pytest tests/unit/` | Runtime API + manager 测试 |
| Python 集成 | pytest | `PYTHONPATH=src python3 -m pytest tests/integration/` | V3 集成验证 |
| Smoke 入口 | Python | `PYTHONPATH=src python3 scripts/runtime_smoke.py` | API 端点最小主链验证 |

---

## 前端测试约定

### Harness 基座 (A42)

所有 composable 测试必须使用 `console/tests/helpers/runtimeHarness.ts` 提供的统一基座：

```typescript
import { withComposable, flushPromises, captureWarnings } from './helpers/runtimeHarness'

// 正确用法：在 Vue setup 上下文中测试 composable
it('useRuntimeLiveData 在 Vue setup 中正确运行', async () => {
  const { result } = await withComposable(() => useRuntimeLiveData())
  expect(result.state.value).toBeDefined()
})
```

**禁止**：
- 直接在测试函数中调用 `const data = useRuntimeLiveData()`（绕过 Vue lifecycle）
- 在测试文件内手写 `flushPromises` 或 `mount` helper

### Mock 约定

Mock 必须在测试文件顶层使用 `vi.mock`（Vitest hoisting 要求）：

```typescript
// 测试文件顶层（hoisted）
vi.mock('../src/services/runtimeApi', async () => {
  const { createRuntimeApiMocks } = await import('./helpers/runtimeHarness')
  return { runtimeApi: createRuntimeApiMocks() }
})

vi.mocked(runtimeApi.status).mockResolvedValue(customStatus)
```

**禁止**：
- 在 `beforeEach` 或测试函数内使用 `vi.mock`
- 使用 `vi.mock` factory 时访问模块导入变量（Vitest 会先执行 factory）

### Sample 数据

使用 `runtimeMockSamples` 导入标准 sample 数据：

```typescript
import { runtimeMockSamples } from './helpers/runtimeHarness'

// 在 vi.mock factory 或 beforeEach 中使用
vi.mocked(runtimeApi.plan).mockResolvedValue(runtimeMockSamples.plan)
```

---

## Python 测试约定

### API 测试

使用 `FastAPI TestClient` 和 mock driver/manager：

```python
from fastapi.testclient import TestClient
from unittest.mock import patch

@pytest.fixture
def client():
    from claudeflow.runtime.api import app
    return TestClient(app)

@pytest.fixture
def mock_driver():
    with patch("claudeflow.runtime.api.driver") as driver:
        yield driver
```

### Smoke 入口 (A44)

`scripts/runtime_smoke.py` 提供最小主链验证：

```bash
PYTHONPATH=src python3 scripts/runtime_smoke.py
```

覆盖端点：
- `/api/runtime/status` - 全局状态
- `/api/runtime/sessions` - 会话列表
- `/api/session/{session_id}/events-list` - 事件列表（最小主链必选）
- `/api/runtime/dispatch` - 调度入口
- `/api/runtime/action-audit` - 审计记录
- `/api/runtime/plan` - 执行计划（额外验证）
- `/health` - 健康检查

---

## 排障顺序

### 前端测试失败

1. **检查 lifecycle warning**
   ```bash
   cd console && npm test 2>&1 | grep -i "onMounted"
   ```
   原因：composable 未在 Vue setup 上下文调用
   解决：使用 `withComposable()` 包装

2. **检查 mock 配置**
   ```bash
   cd console && npm test 2>&1 | grep -i "warn"
   ```
   原因：`vi.mock` 未在顶层 hoisted 或 mock 数据未配置
   解决：检查 `vi.mock` 位置，使用 `runtimeMockSamples` 标准数据

3. **检查 computed 惰性触发**
   原因：Vue computed property 是惰性的，未访问 `.value` 时不会触发 parse/validate
   解决：先访问 `computed.value`，再检查 `parseError`

### Python 测试失败

1. **检查 PYTHONPATH**
   ```bash
   PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py
   ```
   原因：模块导入路径不正确
   解决：确保 `PYTHONPATH=src`

2. **检查 mock driver 状态**
   原因：`TestClient` 使用真实 driver，driver.sessions 为空
   解决：在测试中 mock driver 或创建测试 session

3. **检查 events-list 404**
   原因：session_id 不存在于 driver.sessions
   解决：创建 mock CliSession 并添加到 driver.sessions

---

## Phase 3/4 已收口 Warning

### A41: Action-audit fetch warning

**问题**：`RuntimeConsole.spec.ts` 默认测试打印 "Failed to load action audit" warning

**解决**：
- 在 `vi.mock` 顶层 mock `runtimeApi.listActionAudit`
- 使用 `runtimeMockSamples.auditRecords` 作为返回值
- 不在 `beforeEach` 内创建 mock

### A42: Lifecycle warning 消除

**问题**：composable 测试报 "onMounted is called when there is no active component instance"

**解决**：
- 使用 `withComposable()` 在 Vue setup 上下文测试
- 不在测试函数直接调用 composable

### A43: Parse/validate 错误路径

**问题**：`parseError` 断言失败，值为 null

**解决**：
- 先访问 `computed.value` 触发惰性计算
- 再检查 `state.value.parseError`
- 不假设 computed 已自动运行

---

## 测试干净度验证

### 前端

```bash
cd console && npm test -- --run 2>&1 | grep -i "warn"
# 期望：无 lifecycle warning，无 audit fetch warning
# Node localstorage warning 允许存在（非 blocker）
```

### Python

```bash
PYTHONPATH=src python3 -m pytest tests/unit/ tests/integration/ -v
# 期望：全部 passed，无 error
```

### Smoke

```bash
PYTHONPATH=src python3 scripts/runtime_smoke.py
# 期望：7 passed, 0 failed
```

---

## 文档更新约定

任何涉及以下范围的功能变更，必须同步更新本文档：

- `console/tests/helpers/runtimeHarness.ts`
- `scripts/runtime_smoke.py`
- `src/claudeflow/runtime/api.py`
- `console/src/composables/useRuntime*.ts`

更新规则：
1. 新增测试入口 → 添加到"测试入口总览"
2. 新增 mock 约定 → 添加到"Mock 约定"章节
3. 新增排障场景 → 添加到"排障顺序"
4. 收口新的 warning → 添加到"已收口 Warning"

---

## 参考

- [runtime/changelog.md](changelog.md) - 实现变更记录
- [console/tests/helpers/runtimeHarness.ts](../../console/tests/helpers/runtimeHarness.ts) - 测试基座源码
- [scripts/runtime_smoke.py](../../scripts/runtime_smoke.py) - Smoke 入口源码