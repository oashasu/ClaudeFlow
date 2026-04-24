# Runtime 下一阶段需求规格

> 状态：`pending`
>
> 创建日期：2026-04-24
>
> 适用范围：ClaudeFlow Runtime / Hermes Runtime API / Runtime Console

## 1. 背景

当前仓库已经具备最小可用的 runtime 工作台：

- 可查看 `status / sessions / plan / explain / dispatch`
- 可执行 session 级动作：`intervene / complete / fail`
- `Dashboard / TaskDetail` 已具备进入 Runtime Console 的导航入口

但这套能力仍偏 PoC，主要问题是：

- 动作已可执行，但缺少确认机制与审计记录
- Runtime Console 页面状态职责过重，维护成本偏高
- runtime JSON 协议已相对稳定，但还没有严格 schema 校验
- 调度器仍是最小实现，缺少更接近真实多 Agent 编排的机制

本规格用于定义下一阶段优化内容，暂不在本次提交中直接实现。

## 2. 目标

下一阶段围绕以下四个方向推进：

1. 为 session 级动作增加确认机制和操作审计
2. 将 Runtime Console 收敛为更清晰的状态驱动结构
3. 为 runtime 返回体补齐正式 schema 校验
4. 提升 runtime 调度器的编排能力

## 3. 优先级

### P0：操作确认与审计

目标：

- 为 `intervene / complete / fail` 增加二次确认
- 记录动作审计日志
- 支持查看最近一次动作结果

建议实现点：

- 前端增加操作确认弹层
- 后端记录 action log
- 在 Runtime Console 展示最近操作状态

验收标准：

- 用户触发危险动作时必须先确认
- 每次动作都能看到操作时间、动作类型、目标 task/session、输入摘要、结果状态
- 出错时可以看到明确失败原因

### P1：Runtime Console 结构重构

目标：

- 降低 [RuntimeConsole.vue](/Users/claw/sandbox/personal/claudeflow/console/src/views/RuntimeConsole.vue) 的职责复杂度

建议实现点：

- 提取 `useRuntimeLiveData()` 之类的数据组合逻辑
- 提取 `useRuntimeActions()` 之类的动作组合逻辑
- 让页面更偏向编排组件，而不是堆业务逻辑

验收标准：

- 页面主文件长度和职责明显收敛
- 轮询逻辑、动作逻辑、视图逻辑分层明确
- 测试可以分别覆盖数据流和动作流

### P1：返回体 schema 校验

目标：

- 固化 runtime API 协议，降低前后端字段漂移风险

覆盖对象：

- `status`
- `sessions`
- `plan`
- `explain`
- `dispatch`
- `session events`

建议实现点：

- 后端统一返回 DTO
- 前端对 live payload 做 parse/validate
- `examples/*.schema.json` 同步更新

验收标准：

- 关键返回体具备正式 schema
- 前端对异常 payload 有明确报错，不 silent fail

### P2：调度器增强

目标：

- 从最小调度器推进到更接近真实多 Agent 运行时

建议实现点：

- 让 `shared_files` 真正进入调度决策
- 支持 `IntegrationTask` 的串行集成策略
- 为 `failed` 上游补充重试/回流策略
- 在 `complete/fail` 后提供下一轮 dispatch 建议

验收标准：

- 调度器能解释更多“为什么现在不能跑”
- 共享文件与集成任务具备明确调度规则
- 失败任务不再只有单一阻塞处理方式

## 4. 非目标

本次规格不包含以下内容：

- 重新设计旧 Dashboard 的任务流模型
- 把 Dashboard 和 Runtime Console 合并成单一页面
- 在本阶段引入复杂权限系统
- 在本阶段直接做完整企业级审计平台

## 5. 建议实现顺序

建议按以下顺序分批落地：

1. 操作确认与审计
2. Runtime Console 结构重构
3. runtime schema 校验
4. 调度器增强

## 6. 影响文件范围

预计主要涉及：

- `src/claudeflow/runtime/**`
- `src/claudeflow/hermes_service.py`
- `console/src/views/RuntimeConsole.vue`
- `console/src/components/runtime/**`
- `console/src/services/runtimeApi.ts`
- `examples/runtime-*.schema.json`
- `docs/09_Runtime实现与变更记录.md`

## 7. 待实现标记

当前状态：`pending`

进入实现前，需先基于本规格拆分具体任务，并同步更新实现记录文档。
