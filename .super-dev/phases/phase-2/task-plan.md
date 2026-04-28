# Phase 2 Task Plan

## 状态: ✅ 完成

## 执行顺序

1. `T201` ✅ Review Artifact 模型与写入器
2. `T202` ✅ Result → Review Queue / Submitted 状态集成
3. `T203` ✅ Rework Task Generator
4. `T204` ✅ Gate Report Writer
5. `T205` ✅ Phase Reopen / Advance 状态服务
6. `T206` ✅ 回归与阶段验收测试

## 依赖关系

- `T202` 依赖 `T201`
- `T203` 依赖 `T201 + T202`
- `T204` 依赖 `T201 + T202`
- `T205` 依赖 `T203 + T204`
- `T206` 依赖 `T201 ~ T205`

## 宿主分配策略

- `Claude` 负责实现 `T201 ~ T206`
- `Codex` 继续只承担 Governor 审查与 gate 决策
- 本阶段不允许将主实现任务切回 Codex

## 每个任务的定义

### T201

- 目标: 建立 review artifact 结构与写入能力
- 输出: `reviews/<task-id>-review.md`
- 验收: `A21`

### T202

- 目标: 让 Worker 完成结果进入待审查状态并可回写 state
- 输出: review queue 或等价待审查落盘对象
- 验收: `A22`

### T203

- 目标: 从 review artifact 生成返工任务包
- 输出: `<original-id>-R<n>.yaml`
- 验收: `A23`

### T204

- 目标: 写 gate report 并汇总 phase 审查结果
- 输出: `gate-report.md`
- 验收: `A25`

### T205

- 目标: 实现 phase reopen / advance 决策与 state 回写
- 输出: `pipeline-state.json` 状态更新
- 验收: `A24`, `A26`

### T206

- 目标: 补齐回归与阶段验收测试
- 输出: 测试证据
- 验收: `A27`

## 不属于本阶段

1. 宿主预算 / quota
2. 宿主约束结构化校验
3. Pipeline Console
4. Java / Spring 外部集成
