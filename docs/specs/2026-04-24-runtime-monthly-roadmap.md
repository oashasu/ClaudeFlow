# Runtime 月度迭代路线图（2026-04-24 ~ 2026-05-24）

> 状态：`planned`
>
> 范围：ClaudeFlow Runtime / Hermes Runtime API / Runtime Console

## 1. 目标

未来 1 个月的优化重点不是继续无序加按钮，而是把当前 runtime PoC 推进到“可控、可维护、可验证”的阶段。

路线图拆成 4 个独立规格：

1. [2026-04-24-runtime-action-audit-spec.md](2026-04-24-runtime-action-audit-spec.md)
2. [2026-04-24-runtime-console-refactor-spec.md](2026-04-24-runtime-console-refactor-spec.md)
3. [2026-04-24-runtime-schema-validation-spec.md](2026-04-24-runtime-schema-validation-spec.md)
4. [2026-04-24-runtime-scheduler-enhancement-spec.md](2026-04-24-runtime-scheduler-enhancement-spec.md)

## 2. 推荐排期

### 第 1 周

主题：动作确认与审计

目标：

- 为 `intervene / complete / fail` 增加确认流程
- 建立基础 action log
- 让 runtime 控制台能查看最近操作结果

交付基线：

- 前端具备确认和失败回显
- 后端持久化动作记录
- 文档同步更新

### 第 2 周

主题：Runtime Console 结构重构

目标：

- 把 `RuntimeConsole.vue` 中的数据流、动作流、轮询流拆开
- 降低页面复杂度

交付基线：

- 页面主文件只保留视图拼装
- 数据与动作逻辑有独立可测试模块

### 第 3 周

主题：runtime schema 校验

目标：

- 固化 `status / sessions / plan / explain / dispatch / session events`
- 避免前后端字段漂移

交付基线：

- 文档、sample、schema 三者一致
- live payload 校验失败时能明确报错

### 第 4 周

主题：调度器增强

目标：

- 把 `shared_files / IntegrationTask / fail 回流` 纳入调度器
- 让 runtime 从最小调度器更接近真实工程编排

交付基线：

- 调度器能表达更多阻塞原因
- 集成任务与共享文件具备正式调度规则

## 3. 月度验收标准

1. 所有 4 份规格文档均存在，并有明确状态字段。
2. 每次实现必须同步更新 [09_Runtime实现与变更记录.md](../09_Runtime实现与变更记录.md)。
3. 每个阶段结束都必须有对应测试或验收证据，不能只停留在聊天说明。
4. Runtime Console 不再只是演示视图，而是具备基础可操作、可追踪、可解释能力。
5. 调度层的改动不能破坏现有 `dispatch / plan / explain / status` 基本闭环。
