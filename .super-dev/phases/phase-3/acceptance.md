# Phase 3 Acceptance

## 状态: 待实现

## A31 Runtime Console 结构收口

- 期望
  - `RuntimeConsole.vue` 不再堆叠主要拉数和动作逻辑
  - 页面主职责收敛为组件编排与状态绑定

## A32 高影响动作确认链

- 期望
  - `complete` 与 `fail` 没有确认就不能真正发请求
  - `intervene` 提交前可见目标 `task_id / session_id / prompt` 摘要

## A33 Action Audit 可见

- 期望
  - `intervene / complete / fail` 成功或失败后有可查询记录
  - Console 中可见最近一次动作结果与错误信息

## A34 Runtime 协议校验闭环

- 期望
  - `status / sessions / plan / explain / dispatch / events` 有稳定 schema 或类型约束
  - live payload parse 失败时前端显示结构化错误，而不是静默空白

## A35 Java/HTTP 消费面收口

- 期望
  - Java 控制层明确旧任务流与 runtime 消费边界
  - 不复制 Python runtime 状态机逻辑

## A36 文档与回归

- 期望
  - `docs/runtime/changelog.md`、`docs/README.md`、`examples/*` 与实现同步
  - 不回退 Phase 1 / Phase 2 已验收能力

## Blocker 条件

以下任一项即阻断：

1. Runtime Console 仍由单文件承载主要状态获取与动作实现
2. 高影响动作没有确认链或无审计记录
3. live payload 协议错误被前端静默吞掉
4. Java 消费层复制或偏离 Python runtime 主协议
5. 为完成 Phase 3 而回退 Phase 1 / Phase 2 验收主链
