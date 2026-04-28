# Phase 2 Claude 实现交接

## 角色边界

- `Claude` 负责实现 `T201 ~ T206`
- `Codex` 继续担任 Governor，只做审查、返工裁决、gate 决策
- 本阶段不允许由 Codex 直接承担主实现任务

## 输入文档

- `../research.md`
- `../prd.md`
- `../architecture.md`
- `../uiux.md`
- `../spec.md`
- `../acceptance.md`
- `../task-plan.md`
- `../tasks/T201.yaml`
- `../tasks/T202.yaml`
- `../tasks/T203.yaml`
- `../tasks/T204.yaml`
- `../tasks/T205.yaml`
- `../tasks/T206.yaml`

## 实现总目标

在现有 `runtime + governance + .super-dev` 基础上补齐最小质量门禁闭环：

```text
result collected
→ review-ready
→ review artifact
→ accepted / rework_required
→ gate report
→ reopen / advance
```

## 必须满足

1. 不得重建第二套 runtime / driver / dispatcher
2. review / gate / rework 产物必须落盘
3. 返工任务包必须复用现有 task package schema
4. `pipeline-state.json` 必须与 review/gate 结果一致
5. 不得回退 Phase 1 多宿主执行层能力

## 本阶段不做

1. 宿主预算 / quota
2. 宿主约束结构化校验
3. UI / Console
4. Java / Spring 外部集成

## 回传要求

- `changed_files`
- `summary`
- `test_evidence`
- 如有未完成项，必须逐条列出
