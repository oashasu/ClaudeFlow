# Phase 1 Spec

## 阶段定义

- 阶段 ID: `phase-1`
- 阶段名称: `多宿主执行层`
- 当前目标: 将治理任务包接入 Python runtime 主链，并支持 `claude` / `codex` 双宿主分发

## 核心契约

### 1. RuntimeDriver 接口

最少接口：

- `start_task(task_spec, cwd?) -> DriverSessionStartResult`
- `intervene(session_id, prompt) -> None`
- `cancel(session_id) -> None`
- `get_session(session_id) -> DriverSessionState | None`
- `get_status(session_id) -> str`
- `collect_events(session_id) -> list[event]`
- `collect_result(session_id) -> DriverExecutionResult`

### 2. 宿主枚举

支持：

- `claude`
- `codex`

保留但本阶段不允许真实派发：

- `future`

### 3. Governance Task 到 RuntimeTask 的映射

任务包字段必须进入运行对象：

- `id -> task_id`
- `phase_id -> phase_id`
- `executor_type -> executor_type`
- `inputs -> read_paths/document_refs`
- `allowed_write_paths -> write_paths`
- `constraints -> constraints`
- `acceptance_refs -> acceptance_refs`

### 4. Session Index 最少字段

- `task_id`
- `phase_id`
- `executor_type`
- `driver_name`
- `session_id`
- `worktree`
- `status`
- `summary`
- `changed_files`
- `tests`
- `known_issues`

### 5. Dispatch 规则

1. 优先消费 `.super-dev/phases/phase-1/tasks/*.yaml`
2. governance adapter 将任务包转为 runtime 对象
3. registry 根据 `executor_type` 选 driver
4. 启动后写 session index
5. 不支持宿主必须拒绝 dispatch

### 5.1 主链宿主化决策

Phase 1 必须完成 `runtime` 主链宿主化，不允许只做治理旁路。

以下主链都必须收敛到宿主感知模型：

- `dispatch_runnable_tasks()`
- `start_worker()`
- `explain_task()`
- 默认 session index 写入路径

仅新增 `dispatch_from_governance()` 的旁路实现，不算 Phase 1 通过。

### 5.2 RuntimeTaskSpec 单主模型决策

`RuntimeTaskSpec` 是 Phase 1 运行时主链的唯一目标模型。

要求：

1. `RuntimeTaskSpec` 进入默认 dispatch / explain / running 视图主链。
2. `WorkerTaskSpec` 不得继续作为长期主模型。
3. 如存在旧 task graph 兼容压力，只允许 `WorkerTaskSpec -> RuntimeTaskSpec` 的短期桥接。
4. 不允许 `WorkerTaskSpec` 与 `RuntimeTaskSpec` 长期双主模型并存。

### 6. CLI / API 最小要求

CLI 至少支持一条治理入口闭环：

- `runtime dispatch --governance-root <root> --phase-id phase-1`

如果实现阶段保留 graph 中间层，也必须由 ClaudeFlow 自动生成，不允许 Governor 手工维护平行 graph 文件。

API / CLI 输出至少包含：

- `task_id`
- `executor_type`
- `driver_name`（若已分配）
- `state`
- `reason_code`
- `reason`

## 失败处理

- `unsupported_executor_type`
- `driver_not_registered`
- `driver_start_failed`
- `result_collection_failed`

## 质量围栏

1. 不得把 `owner_role` 冒充 `executor_type`。
2. 不得只补测试，不改 runtime 主链。
3. 不得在 RuntimeManager 中硬编码宿主逻辑替代 registry。
4. 不得在本阶段混入 review/rework/advance 自动闭环。
5. 不得保留“旧单宿主主链 + 新多宿主旁路”双轨运行。
6. 不得让 `WorkerTaskSpec` 继续充当默认 dispatch 主模型。
