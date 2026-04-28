# Phase 5 Task Plan

## 状态: 待分发

## 执行顺序

1. `T501` release checklist 与 quality gate 矩阵固化
2. `T502` 统一发布门禁命令入口或命令组
3. `T503` release readiness / warning budget / blocker 分层文档
4. `T504` 发布后验证与 release smoke 说明
5. `T505` 回滚约定与交付摘要模板
6. `T506` Phase 5 回归与阶段验收测试

## 依赖关系

- `T502` 依赖 `T501`
- `T503` 依赖 `T501 + T502`
- `T504` 依赖 `T501 + T502`
- `T505` 依赖 `T503 + T504`
- `T506` 依赖 `T501 ~ T505`

## 宿主分配策略

- `Claude` 负责 Phase 5 实现任务
- `Codex` 继续负责 Governor 审查与 gate 决策
- 本阶段先收口文档/脚本级发布门禁，再做回归与交付决策

## 每个任务的定义

### T501

- 目标: 固化 release checklist 与 quality gate 矩阵
- 输出: 发布前检查清单、门禁顺序、命令矩阵
- 验收: `A51`, `A52`

### T502

- 目标: 建立统一发布门禁入口或统一命令组
- 输出: 可复跑的 release gate 执行方式
- 验收: `A52`

### T503

- 目标: 固化 release readiness、warning budget、blocker 分层
- 输出: 发布判定标准与 warning 分类口径
- 验收: `A53`

### T504

- 目标: 同步发布后验证说明与关键主链验证步骤
- 输出: post-release verification 文档或脚本说明
- 验收: `A54`

### T505

- 目标: 固化回滚约定与交付摘要模板
- 输出: rollback runbook + delivery summary 模板
- 验收: `A55`

### T506

- 目标: 补齐 Phase 5 回归与阶段验收测试
- 输出: release-ready / not-ready 决策证据
- 验收: `A51`, `A52`, `A53`, `A54`, `A55`, `A56`

## 不属于本阶段

1. 新 Runtime Console 功能
2. 新 runtime API 业务能力
3. 前端测试 harness 二次重构
4. 大规模 CI/CD 平台迁移
5. 生产自动部署系统重写
