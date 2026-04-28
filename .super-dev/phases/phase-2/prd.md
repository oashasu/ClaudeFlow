# Phase 2 PRD

## 阶段定位

Phase 2 负责把 ClaudeFlow 从“能派发执行”推进到“能完成质量门禁闭环”。

## 用户故事

### US-1 Governor 审查

作为 Governor，我需要在 Worker 返回结果后看到结构化待审查对象，并输出标准化 review artifact，而不是手工拼接结论。

### US-2 Rework 自动生成

作为 Governor，当 review 判定 `rework_required` 时，我需要自动生成返工任务包，避免手工复制原任务约束和 findings。

### US-3 Phase Gate 决策

作为 Governor，当一个 phase 下的任务通过审查后，我需要得到结构化的 gate report，并决定：

- `accepted`
- `reopened`
- `advance`

### US-4 审计追踪

作为项目管理者，我需要所有 review / gate / rework 决策都有落盘证据，后续可回溯。

## 范围

### In Scope

1. review artifact 文件规范与写入
2. review-ready 队列或等价落盘对象
3. rework task package 自动生成
4. gate report 文件规范与写入
5. `pipeline-state.json` 中任务/阶段状态更新

### Out of Scope

1. 控制台展示
2. 配额系统
3. Markdown 约束自动解析
4. Java/HTTP 外部系统消费

## 功能要求

1. Worker 结果回收后，必须进入 `submitted` 或 `under_review` 状态
2. Governor review 通过后，任务状态必须进入 `accepted`
3. Governor review 失败后，原任务状态必须进入 `rework_required`
4. 返工任务包必须继承：
   - `phase_id`
   - `allowed_write_paths`
   - `acceptance_refs`
   - 原任务关键约束
   - 当前 review findings 引用
5. gate report 必须可区分：
   - 全通过，可 advance
   - 有 blocker，需 reopen

## 质量围栏

1. 不得让聊天结论替代 review artifact
2. 不得生成脱离原 schema 的返工任务格式
3. 不得隐式修改原任务包关键约束
4. 不得跳过 `pipeline-state.json` 状态回写
