# Phase 4 Spec

## 阶段定义

- 阶段 ID: `phase-4`
- 阶段名称: `Runtime Console 测试与可观测性收尾`

## 核心能力

### 1. Warning Cleanup

目标：

- 清理 Runtime Console 相关测试中的已知 lifecycle 与 audit fetch 噪音

最小要求：

1. `RuntimeConsole.spec.ts` 运行时不再打印默认 audit fetch warning
2. `runtimeLiveDataValidation.spec.ts` 不再通过裸调用 composable 触发生命周期 warning
3. 若仍保留 warning，必须具备明确、受控的 budget 与理由

### 2. Shared Frontend Test Harness

目标：

- 为 composable / runtime API 交互建立统一测试基座

最小要求：

1. 提供共享的 setup/mount/harness 入口
2. 提供共享的 runtime API mock 约定
3. 提供统一的异步 flush 与错误断言方式

### 3. Stable Error-Path Coverage

覆盖对象：

- `action-audit`
- `status`
- `sessions`
- `session events`

最小要求：

1. success / empty / error 路径都有稳定断言
2. parse / validate 失败不产生不可控控制台噪音
3. UI 状态与测试断言口径一致

### 4. Runtime Smoke Entry

最小要求：

1. 提供一条真实可运行入口
2. 覆盖 status、sessions、events，以及 explain|dispatch、action result|audit 中至少各一条
3. smoke 结果能作为 governor 审核证据引用

### 5. Testing / Observability Docs

最小要求：

1. 文档说明测试基座如何使用
2. 文档说明 smoke 如何运行
3. 文档说明 warning / parse error / fetch error 的优先排查顺序

## 状态流转

### phase.status

```text
docs_confirm
→ ready_for_dispatch
→ in_execution
→ implementation_review
→ quality_gate
→ accepted
```

### task.status

```text
planned
→ dispatched
→ implementing
→ submitted
→ under_review
→ accepted
```

或：

```text
planned
→ dispatched
→ implementing
→ submitted
→ under_review
→ rework_required
```

## 非法情况

以下情况必须阻断：

1. 只 suppress console 输出，不修正测试隔离或错误路径
2. 继续在各个 spec 内分散复制 mock / mount / flush 逻辑
3. smoke 入口不可运行或只覆盖 sample 静态文件而不经过真实主链
4. 文档与测试基座实现不一致
5. 为了保持测试绿而把 Runtime Console 的错误反馈静默化

## 质量围栏

1. 不新增第二套 Runtime Console 或第二套测试风格
2. 不把测试隔离逻辑污染到生产主链
3. 不允许 warning 清理通过删断言完成
4. 不允许把 smoke 写成仅供人工阅读的文档说明
