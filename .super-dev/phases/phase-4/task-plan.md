# Phase 4 Task Plan

## 状态: 待分发

## 执行顺序

1. `T401` 前端测试 harness 与 mock 基座收口
2. `T402` Runtime Console warning 清理与审计链测试隔离
3. `T403` live data / parse validate 错误路径稳定化
4. `T404` runtime smoke 最小主链入口
5. `T405` 测试与可观测性文档同步
6. `T406` Phase 4 回归与阶段验收测试

## 依赖关系

- `T402` 依赖 `T401`
- `T403` 依赖 `T401`
- `T404` 依赖 `T402 + T403`
- `T405` 依赖 `T401 + T402 + T403 + T404`
- `T406` 依赖 `T401 ~ T405`

## 宿主分配策略

- `Claude` 负责 Phase 4 实现任务
- `Codex` 继续负责 Governor 审查与 gate 决策
- 本阶段继续以前端测试基座优先，再推进 smoke 与文档收口

## 每个任务的定义

### T401

- 目标: 收口 composable/runtime API 相关共享测试 harness 与 mock 基座
- 输出: 统一 setup/mount/mock/flush 入口
- 验收: `A42`

### T402

- 目标: 清理 Runtime Console 相关已知 warning，并稳定 action audit 测试隔离
- 输出: warning-free 或受控 warning-budget 的 console 测试
- 验收: `A41`, `A43`

### T403

- 目标: 收口 live data / parse validate 的错误路径测试与状态断言
- 输出: 可预测的错误路径覆盖
- 验收: `A42`, `A43`

### T404

- 目标: 提供 runtime smoke 最小主链入口
- 输出: 可复跑 smoke 脚本或集成测试入口
- 验收: `A44`

### T405

- 目标: 同步 testing / observability 文档与排障说明
- 输出: 使用说明、排障顺序、维护口径
- 验收: `A45`

### T406

- 目标: 补齐 Phase 4 回归与阶段验收测试
- 输出: 测试证据与 Phase 4 质量门禁
- 验收: `A41`, `A42`, `A43`, `A44`, `A45`, `A46`

## 不属于本阶段

1. 发布工程化 / CI/CD
2. release checklist / rollback runbook
3. 新 Runtime Console 功能
4. Java/HTTP 发布流水线
