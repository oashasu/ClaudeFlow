# Phase 2 Acceptance

## 状态: ✅ 全部验收通过

## A21 Review Artifact 落盘 ✅

- 期望
  - Governor 审查后能生成标准化 review artifact
  - 文件路径和命名可由 `phase_id + task_id` 稳定定位

## A22 结果进入待审查状态 ✅

- 期望
  - Worker 结果回收后进入 `submitted` 或 `under_review`
  - `pipeline-state.json` 可见状态变化

## A23 返工任务自动生成 ✅

- 期望
  - review 判定 `rework_required` 后生成返工任务包
  - 返工任务包继承原任务关键约束

## A24 Accepted 路径 ✅

- 期望
  - review 判定 `accepted` 后原任务进入 `accepted`
  - 不生成多余 rework task

## A25 Gate Report 落盘 ✅

- 期望
  - phase 级 gate report 能统计 accepted / rework / blocker 状态
  - 可给出 `advance_allowed / reopen_required`

## A26 Phase Reopen / Advance ✅

- 期望
  - 全部通过时 phase 可推进
  - 存在 blocker 或返工时 phase 不得推进，并可 reopen

## A27 回归 ✅

- 期望
  - 不回退 Phase 1 已完成能力
  - `dispatch_runnable_tasks / dispatch_from_governance / RuntimeTaskSpec` 主链保持成立

## Blocker 条件

以下任一项即阻断：

1. review artifact 未落盘却宣称通过
2. rework task 生成后丢失原写路径或验收引用
3. gate report 缺失却允许 advance
4. `pipeline-state.json` 与 review/gate 产物状态不一致
