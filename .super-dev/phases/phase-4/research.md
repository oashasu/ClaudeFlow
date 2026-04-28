# Phase 4 Research

## 阶段名称

- `phase-4`
- `Runtime Console 测试与可观测性收尾`

## Phase 3 后的真实缺口

Phase 3 已经完成了 Runtime Console、action audit、runtime schema/validator，以及 Java/HTTP 消费契约的主交付。但从 governor 审核结果看，仍有一批不阻断验收、却会持续侵蚀交付稳定性的残留问题：

1. Console 测试仍会打印 `action-audit` 的 fetch warning，说明测试环境对 live/audit 拉取链的隔离还不完整
2. `runtimeLiveDataValidation.spec.ts` 直接调用 composable，触发 Vue lifecycle warning，说明测试 harness 仍绕过了真实 setup 环境
3. 当前前端回归更偏“断言通过”，而不是“测试信号干净、失败定位明确、无噪音”
4. runtime smoke 的文档和历史 spec 已存在，但仓库里还缺一条稳定、可复跑、能串起关键 runtime 主链的轻量门禁

这些问题不再属于 Phase 3 的功能性缺口，而属于交付质量面的“最后一公里”。

## 本阶段目标

Phase 4 的目标不是新增能力，而是把 Runtime Console 的验证链收束为一套可长期维护的质量基线：

```text
Runtime Console UI / composables / runtime API mocks
→ 测试隔离与 harness 收口
→ warning-free 或 warning-budget 明确
→ audit / validation / live path 稳定回归
→ runtime smoke 最小真链可复跑
```

## 本阶段优先级判断

### P0

1. 清理当前前端测试中的非阻断 warning
2. 为 composable / live data / action audit 建立稳定的测试隔离层
3. 增加 runtime smoke 入口，验证最小主链可运行

### P1

1. 统一前端测试中的 mock、mount 和异步 flush 模式
2. 收敛 action audit 测试噪音与错误输出口径
3. 补充 observability 文档，明确“看哪里、测什么、失败时如何定位”

## 本阶段范围

### In Scope

1. `console/tests/**` 中 Runtime Console 相关用例的 warning 清理
2. `useRuntimeLiveData` / `useRuntimeActions` 的测试 harness 与 mock 收口
3. action audit fetch 测试隔离、错误路径稳定化
4. runtime smoke 脚本或最小集成验证入口
5. 文档中的测试/可观测性说明同步

### Out of Scope

1. 新增 Runtime Console 新功能
2. Java/HTTP 发布工程化与 CI/CD 编排
3. 新一轮 schema 扩展
4. 宿主调度、governance 状态机重构
5. 发布流程、部署说明、回滚策略

## 关键设计判断

1. Phase 4 应该把“测试能过”提升为“测试输出可信、无多余噪音、定位路径清晰”
2. 对于 action audit 与 live data，不应继续在每个 spec 各自造 mock，而应形成共享测试基座
3. runtime smoke 不需要覆盖所有细节，但必须覆盖 status / sessions / explain / action 这类核心主链的最小闭环
4. 当前阶段只收口 Console 与 runtime 可观测性；发布工程化明确延后到 Phase 5，避免两个主题混线

## 阶段完成定义

只有同时满足以下条件，Phase 4 才算完成：

1. Runtime Console 相关测试默认运行时不再打印已知 warning 噪音，或有明确且受控的 warning budget
2. composable 测试运行在真实 Vue setup/harness 之上，而不是裸调用
3. action audit 与 live payload 的成功/失败路径都能稳定断言，且错误输出可预测
4. 存在一条可复跑的 runtime smoke 入口，用于覆盖最小主链
5. 文档能够指导后续维护者快速判断“测试失败是产品问题、契约问题还是 harness 问题”
