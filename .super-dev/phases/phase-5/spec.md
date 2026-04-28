# Phase 5 Spec

## 阶段定义

- 阶段 ID: `phase-5`
- 阶段名称: `交付与发布工程化`

## 核心能力

### 1. Release Checklist

目标：

- 把现有多侧测试与文档一致性检查整理为明确的发布前清单

最小要求：

1. checklist 覆盖 Python、Console、Java、smoke、文档/状态一致性
2. checklist 能被交付执行者按顺序复跑
3. checklist 结果可直接作为 governor 审核证据

### 2. Unified Quality Gate

目标：

- 提供统一的发布门禁执行入口或统一命令组

最小要求：

1. 发布前门禁命令有固定顺序
2. 入口调用仓库中现有真实命令，而不是伪封装
3. 失败时能快速定位是哪一侧门禁失效

### 3. Release Readiness Classification

覆盖对象：

- blocker
- non-blocker
- warning budget
- environment warning

最小要求：

1. 功能性回归与环境级 warning 明确分层
2. `release-ready / not-ready` 有可复述的判断标准
3. governor review 与发布文档口径一致

### 4. Post-Release Verification

最小要求：

1. 定义最小发布后验证链
2. 覆盖 runtime status、sessions、events、dispatch|audit 等关键主链
3. 验证命令可在仓库内直接引用

### 5. Rollback Contract

最小要求：

1. 明确触发回滚的 blocker 条件
2. 明确回滚后需要重验的关键门禁
3. 文档与交付摘要引用同一套口径

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

1. 只写发布文档，不提供真实命令或脚本入口
2. 把局部测试通过误写成整体 release-ready
3. 用环境级 warning 掩盖功能性回归，或反过来把环境噪音错误升级为 blocker
4. 发布后验证与回滚说明无法直接执行
5. 文档、review artifact、pipeline-state 三者口径不一致

## 质量围栏

1. 不新增脱离现状的理想化发布平台设定
2. 不重写 Runtime 主代码来迁就发布流程
3. 不允许把 release engineering 变成另一个 UI/产品开发阶段
4. 不允许发布门禁通过删测试、降标准或跳过关键链路实现
