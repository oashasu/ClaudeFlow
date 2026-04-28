# Phase 4 Architecture

## 总体方案

Phase 4 采用“先收口测试基座，再补 smoke 与 observability 文档”的方案：

```text
runtimeApi.ts / composables / RuntimeConsole
        ↓
shared test harness + runtime API mock layer
        ↓
warning-free unit/spec regression
        ↓
runtime smoke entry
        ↓
observability & troubleshooting docs
```

## 模块职责

### 1. Runtime Console 主代码

职责：

- 保持 Phase 3 已交付的功能主链稳定
- 为测试提供可注入、可隔离的依赖边界

主路径：

- `console/src/views/RuntimeConsole.vue`
- `console/src/composables/useRuntimeLiveData.ts`
- `console/src/composables/useRuntimeActions.ts`
- `console/src/services/runtimeApi.ts`

### 2. 前端测试基座

职责：

- 提供统一 mount / setup / flush / mock 入口
- 消除 composable 裸调用造成的 lifecycle warning
- 统一拦截 runtime API 与 audit fetch

建议结构：

```text
console/tests/helpers/**
console/tests/runtime*.spec.ts
```

### 3. Runtime Smoke 层

职责：

- 覆盖 runtime 最小主链
- 作为单元测试之外的轻量运行态证据

建议入口：

```text
scripts/runtime-smoke-test.sh
tests/integration/test_runtime_smoke.py
```

最终形态以现有仓库脚本生态为准，不强制两者同时存在，但至少要有一条真实可运行入口。

### 4. Observability 文档层

职责：

- 记录测试入口、日志口径、失败排查顺序
- 把 phase 审核中积累的 warning/噪音经验变成维护文档

主路径：

- `docs/runtime/changelog.md`
- `docs/runtime/*.md`
- 必要时新增 `docs/runtime/testing-observability.md`

## 数据与验证流

### 1. Frontend 测试链

```text
test harness mount
→ composable setup
→ mocked runtime API
→ Runtime Console / composable assertions
→ warning-free result
```

### 2. Audit 错误路径链

```text
mocked audit fetch fail
→ normalized error handling
→ predictable UI/test state
→ no uncontrolled console noise
```

### 3. Runtime Smoke 链

```text
runtime init/start or sample bootstrap
→ status / sessions read
→ events / explain / action visibility check
→ smoke pass/fail signal
```

## 架构约束

1. 不回退或重写 Phase 3 的 Runtime Console 页面结构
2. 不把测试隔离逻辑反向污染生产代码主路径
3. 优先通过共享 harness 和依赖注入收口，不用在每个 spec 各自 patch 生命周期
4. smoke 必须是真实入口，不是 README 里的伪命令
5. 若为了 suppress warning 引入额外包装，必须保留失败路径可观察性

## 阶段验收焦点

1. Console 测试是否从“能过”变成“干净且稳定”
2. action audit 和 live data 的错误路径是否不再制造噪音
3. runtime smoke 是否能提供超出单测的最小运行态信号
