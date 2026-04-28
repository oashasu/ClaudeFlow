# Phase 2 验收范围清单

## 结论

Phase 2 本次验收只覆盖“质量门禁闭环”能力，不把当前工作区里的全部改动都算作本次交付。

## 属于本次验收范围

以下改动直接支撑 `T201 ~ T206` 和 `A21 ~ A27`，应纳入本次验收判断：

### 1. 治理主模块

- `.super-dev/pipeline-state.json`
- `.super-dev/phases/phase-2/acceptance.md`
- `.super-dev/phases/phase-2/gate-report.md`
- `.super-dev/phases/phase-2/spec.md`
- `.super-dev/phases/phase-2/task-plan.md`
- `.super-dev/phases/phase-2/tasks/T201.yaml`
- `.super-dev/phases/phase-2/tasks/T202.yaml`
- `.super-dev/phases/phase-2/tasks/T203.yaml`
- `.super-dev/phases/phase-2/tasks/T204.yaml`
- `.super-dev/phases/phase-2/tasks/T205.yaml`
- `.super-dev/phases/phase-2/tasks/T206.yaml`
- `src/claudeflow/governance/review_artifact.py`
- `src/claudeflow/governance/review_queue.py`
- `src/claudeflow/governance/rework_generator.py`
- `src/claudeflow/governance/gate_report.py`
- `src/claudeflow/governance/phase_gate_service.py`
- `src/claudeflow/governance/pipeline_state.py`

### 2. Phase 2 直接测试证据

- `tests/unit/test_review_artifact.py`
- `tests/unit/test_review_queue.py`
- `tests/unit/test_rework_generator.py`
- `tests/unit/test_gate_report.py`
- `tests/unit/test_phase_gate_service.py`
- `tests/unit/test_phase1_regression.py`

### 3. 与验收直接相关的回归链

这些文件不是 Phase 2 新主题本身，但用于证明“不回退 Phase 1 主链”，因此属于本次验收证据的一部分：

- `tests/unit/test_phase1_multi_host.py`
- `tests/unit/test_runtime_api.py`
- `src/claudeflow/runtime/driver_base.py`
- `src/claudeflow/runtime/manager.py`
- `src/claudeflow/runtime/governance_adapter.py`
- `src/claudeflow/runtime/api.py`

## 不属于本次验收范围

以下改动即使真实存在，也不应影响“Phase 2 是否通过”的结论。它们要么属于下一阶段，要么属于仓库整理，要么属于运行产物。

### 1. 下一阶段候选改动

这些改动更接近 `Pipeline Console / Java HTTP 外部消费面`，建议在 Phase 3 处理：

- `console/src/components/StatsCard.vue`
- `console/src/components/TaskCard.vue`
- `console/src/components/CreateTask.vue`
- `console/src/components/EventStream.vue`
- `console/src/main.ts`
- `console/src/services/api.ts`
- `console/src/services/runtimeApi.ts`
- `console/src/services/sse.ts`
- `console/src/stores/taskStore.ts`
- `console/vite.config.ts`
- `src/main/java/com/claudeflow/controller/TaskController.java`
- `src/main/java/com/claudeflow/service/TaskService.java`
- `src/main/java/com/claudeflow/dto/CreateTaskRequest.java`
- `src/main/java/com/claudeflow/scheduler/TaskScheduler.java`
- `src/main/resources/application.yml`

### 2. 历史模块清理和结构迁移

这些更像仓库重构或历史兼容层收缩，不属于 Phase 2 门禁闭环的通过条件：

- `src/claudeflow/checkpoint.py`
- `src/claudeflow/cli_driver.py`
- `src/claudeflow/employee_pool.py`
- `src/claudeflow/haiku_client.py`
- `src/claudeflow/hermes_service.py`
- `src/claudeflow/knowledge_retrieval.py`
- `src/claudeflow/phase_reviewer.py`
- `src/claudeflow/progress_reporter.py`
- `src/claudeflow/scheduler.py`
- `src/claudeflow/state_machine.py`
- `src/claudeflow/task_manager.py`
- `src/claudeflow/task_reviewer.py`
- `src/claudeflow/governance/acceptance.py`
- `src/claudeflow/governance/circuit_breaker.py`
- `src/claudeflow/governance/config.py`
- `src/claudeflow/governance/recovery.py`
- `src/claudeflow/governance/similarity.py`
- `src/claudeflow/governance/snapshot.py`

### 3. 文档迁移与目录整理

这些改动可以继续保留，但不作为 Phase 2 验收阻断项：

- `README.md`
- `CLAUDE.md`
- `docs/INDEX.md`
- `docs/README.md`
- `docs/archive/**`
- `docs/operations/**`
- `docs/runtime/**`
- `docs/specs/**`
- 历史 `docs/01_* ~ docs/09_*` 删除项

### 4. 运行产物与缓存噪音

这些应视为待清理噪音，不应进入验收判断：

- `.coverage`
- `src/claudeflow.egg-info/**`
- `src/claudeflow/__pycache__/**`
- `tests/**/__pycache__/**`
- `target/**`
- `tasks/task_001/reviews/task_review.json`
- `tasks/task_002/reviews/task_review.json`
- `tasks/task_003/reviews/task_review.json`

## 验收判定规则

1. 只要 Phase 2 范围内的治理模块、状态落盘和测试证据闭环成立，就可以判定本阶段通过。
2. 下一阶段候选改动和运行产物噪音不应反向污染本阶段验收结论。
3. 若后续要做仓库级发布或合并，仍需单独执行一次工作区收口，不要把“阶段验收通过”和“仓库已整理完毕”混为一谈。
