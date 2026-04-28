# Phase 1 PRD

## 阶段目标

让 ClaudeFlow 从“单宿主 CLI 运行器”升级为“按 Governor 任务包执行的多宿主执行层”。

## 用户价值

- Governor 不再手工搬运另一套 task graph
- ClaudeFlow 能按 `executor_type` 选择执行宿主
- Claude / Codex 结果可统一回收，供后续 review/gate 使用

## 功能需求

1. 定义统一 RuntimeDriver 接口。
2. 将现有 Claude CLI 能力收敛为 `ClaudeDriver`。
3. 新增 `CodexDriver` 最小执行路径。
4. 将治理任务包转换为 runtime 可执行任务。
5. 根据 `executor_type` 进行 dispatch。
6. session index 增加宿主信息与统一结果字段。
7. CLI/API 至少有一条治理输入到 dispatch 的闭环路径。

## 非目标

1. 不做自动审查。
2. 不做自动返工。
3. 不做 quality gate 闭环。
4. 不做 Java 后端宿主调度改造。
5. 不做 UI。

## 通过标准

- `executor_type` 真正进入 runtime dispatch
- `claude` 和 `codex` 两条宿主路径都有测试覆盖
- Governor 可通过 `.super-dev` 任务包触发分发
- 统一结果回收结构可用
