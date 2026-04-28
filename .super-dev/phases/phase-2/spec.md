# Phase 2 Spec

## 阶段定义

- 阶段 ID: `phase-2`
- 阶段名称: `质量门禁闭环`

## 核心能力

### 1. Review Artifact

文件路径：

```text
.super-dev/phases/<phase-id>/reviews/<task-id>-review.md
```

最小结构：

- `task_id`
- `phase_id`
- `review_status`
- `decision`
- `blocker_findings`
- `non_blocker_findings`
- `acceptance_result`

允许的 `decision`：

```text
accepted | rework_required
```

### 2. Review Queue

Worker 结果被回收后，系统必须能把任务放入待审查状态。

最小要求：

1. `pipeline-state.json.tasks.<id>.status` 进入 `submitted` 或 `under_review`
2. Governor 可以定位到：
   - 结果摘要
   - changed files
   - tests
   - known issues

### 3. Rework Task Generation

返工任务文件路径：

```text
.super-dev/phases/<phase-id>/tasks/<original-id>-R<n>.yaml
```

返工任务必须继承：

- `phase_id`
- `executor_type`
- `allowed_write_paths`
- `acceptance_refs`
- `gate_on_complete`

返工任务必须新增：

- `rework_context.original_task_id`
- `rework_context.findings_ref`
- `rework_context.rework_round`

### 4. Gate Report

文件路径：

```text
.super-dev/phases/<phase-id>/gate-report.md
```

最小结构：

- `phase_id`
- `gate_status`
- `accepted_tasks`
- `rework_required_tasks`
- `blocker_count`
- `advance_allowed`
- `reopen_required`

### 5. Phase Reopen / Advance

当所有任务通过 review：

- `advance_allowed = true`
- `reopen_required = false`
- phase 可进入 `accepted`

当存在 blocker 或返工任务：

- `advance_allowed = false`
- `reopen_required = true`
- phase 进入 `reopened` 或保持 `implementation_review`

## 状态流转

### task.status

```text
implementing
→ submitted
→ under_review
→ accepted
```

或：

```text
implementing
→ submitted
→ under_review
→ rework_required
```

### phase.status

```text
in_execution
→ implementation_review
→ quality_gate
→ accepted
```

或：

```text
in_execution
→ implementation_review
→ reopened
```

## 非法情况

以下情况必须阻断：

1. 未生成 review artifact 就把任务标记为 `accepted`
2. review 判定 `rework_required` 但未生成返工任务包
3. gate report 缺失却推进 phase
4. 返工任务未继承原任务 `allowed_write_paths`

## 质量围栏

1. 不得发明第二套 review 状态枚举
2. 不得把 review findings 仅保存在聊天上下文
3. 不得用自由文本代替结构化 phase 决策
