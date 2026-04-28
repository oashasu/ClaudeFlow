# Phase 3 Spec

## 阶段定义

- 阶段 ID: `phase-3`
- 阶段名称: `Runtime Console 与外部消费面收口`

## 核心能力

### 1. Console 结构重构

目标：

- 将 `RuntimeConsole.vue` 从“单文件堆逻辑”收敛为“composable + validator + component assembly”

最小要求：

1. 页面层只负责编排与事件绑定
2. 数据获取逻辑进入独立 composable
3. 动作执行逻辑进入独立 composable
4. 协议 parse / validate 在进入 UI 前完成

### 2. Action Confirmation + Audit

覆盖动作：

- `intervene`
- `complete`
- `fail`

最小要求：

1. `complete` 与 `fail` 必须二次确认
2. `intervene` 提交前必须展示目标摘要
3. 每次动作必须产出结构化审计记录
4. Console 可查看最近动作结果和失败错误

### 3. Runtime Protocol Validation

覆盖对象：

- `status`
- `sessions`
- `plan`
- `explain`
- `dispatch`
- `session events`

最小要求：

1. 每类对象有 schema 或稳定类型定义
2. 每类对象有 sample
3. 前端 parse 失败时给出明确错误

### 4. Java/HTTP Consumption Boundary

最小要求：

1. Java 控制层区分旧任务流接口与 runtime 消费接口
2. 不复制 Python runtime 状态机
3. 需要聚合时只做 DTO 转换，不重写核心判定逻辑

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

1. 未做协议校验就让 live payload 直接进入视图
2. 无确认直接执行 `complete` 或 `fail`
3. action 结果成功/失败后没有可回查记录
4. Java 层另起一套字段约定脱离 runtime 协议
5. 只改文档或 sample，不接入真实调用链

## 质量围栏

1. 不得新增第二套 Runtime Console 页面
2. 不得把 parse 失败降级为静默空列表
3. 不得把 action audit 只保存在临时前端状态里
4. 不得为了兼容旧页面而继续扩大 `RuntimeConsole.vue` 的职责
