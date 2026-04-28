# Phase 1 Acceptance

## A01 Driver 抽象建立

- 期望
  - `ClaudeDriver` 与 `CodexDriver` 实现同一驱动协议
  - `RuntimeManager` 不再直接依赖单一 `CliDriver`

## A02 Claude 路径可运行

- 期望
  - `executor_type=claude` 正确选择 `ClaudeDriver`
  - 建立 session index

## A03 Codex 路径可运行

- 期望
  - `executor_type=codex` 正确选择 `CodexDriver`
  - 建立 session index

## A04 不支持宿主被拒绝

- 期望
  - `future` 或未注册宿主返回结构化错误
  - 不创建伪 session index

## A05 治理任务包进入 dispatch 主链

- 期望
  - `.super-dev/phases/phase-1/tasks/*.yaml` 可直接或经自动转换进入 dispatch
  - `executor_type / write_paths / acceptance_refs` 进入运行对象

## A06 Session Index 宿主字段完整

- 期望
  - 至少包含 `executor_type / driver_name / session_id / worktree / status`

## A07 结果回收统一

- 期望
  - `claude` / `codex` 结果都能映射到统一结构：
    - `summary`
    - `changed_files`
    - `tests`
    - `known_issues`

## A08 CLI / API 输出宿主信息

- 期望
  - `runtime plan/explain/dispatch` 输出中带 `executor_type`
  - 派发后可见 `driver_name`

## Blocker 条件

以下任一项即阻断：

1. runtime 主链仍只能跑 `claude`
2. `executor_type` 没进入结构化调度对象
3. `CodexDriver` 只是占位类，未进入派发路径
4. session index 未记录宿主信息
5. Governor 仍要手工维护平行 task graph
