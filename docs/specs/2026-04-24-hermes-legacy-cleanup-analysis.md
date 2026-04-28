# Hermes 遗留清理与 Runtime 核心收敛分析

> 状态：`analysis`
>
> 日期：2026-04-24
>
> 目的：为后续“Hermes 遗留清理”提供准确边界，避免误删当前 runtime-poc 仍在依赖的模块、接口和测试。

## 1. 结论摘要

当前仓库不是“只剩一个 Hermes 壳”，而是：

- `runtime-poc` 已经成为新核心
- 旧 `V1 / V2 / V3` 模块仍作为：
  - 包导出层的一部分
  - 测试依赖的一部分
  - 前端接口依赖的一部分
  - 兼容层的一部分

因此，不能直接做“物理删除式清理”，必须先完成：

1. API 迁移
2. 导出层收缩
3. 测试迁移或废弃
4. 兼容层移除
5. 最后才是物理删除遗留模块

## 2. 当前代码分层判断

### 2.1 当前核心

以下模块属于当前 runtime-poc 的有效核心：

- `src/claudeflow/runtime/cli_driver.py`
- `src/claudeflow/runtime/manager.py`
- `src/claudeflow/cli.py`
- `console/src/views/RuntimeConsole.vue`
- `console/src/services/runtimeApi.ts`

这些模块构成了当前最小可用闭环：

- Claude CLI 多会话驱动
- task graph 调度
- worktree + 写锁
- runtime API
- Runtime Console

### 2.2 兼容层

以下文件本质上是 re-export/兼容入口：

- `src/claudeflow/cli_driver.py`
- `src/claudeflow/runtime_manager.py`
- `src/claudeflow/checkpoint.py`
- `src/claudeflow/scheduler.py`
- `src/claudeflow/state_machine.py`
- `src/claudeflow/task_manager.py`

这些文件可以清理，但前提是：

- 先修改所有导入方
- 先修改相关测试
- 先收缩 `__init__.py`

### 2.3 历史主线模块

以下模块在概念上已不是主线，但工程上仍然活着：

- `workflow/*`
- `alert_handler.py`
- `progress_reporter.py`
- `websocket_client.py`
- `session_utils.py`
- `haiku_client.py`
- `phase_reviewer.py`
- `task_reviewer.py`
- `knowledge_retrieval.py`
- `employee_pool.py`
- `governance/*`

这些模块不能直接被视为“无引用垃圾”，因为：

- 包导出层仍然暴露它们
- 测试仍覆盖它们
- 部分前端或集成链路仍间接依赖其概念

## 3. 关键误判修正

### 3.1 `hermes_service.py` 不能只迁移 `/api/runtime/*`

当前前端不只使用 runtime 端点，还使用 session 端点：

- `POST /api/session/{session_id}/intervene`
- `GET /api/session/{session_id}/events-list`
- 旧任务流里还存在 session/status 等依赖

所以正确动作不是：

- “只迁 runtime 端点后删除 `hermes_service.py`”

而是：

- “先迁移完整的 `runtime + session` 服务端点，再删除 `hermes_service.py`”

### 3.2 wrapper 不能先删

根目录 wrapper 文件目前仍被测试与兼容导入使用。  
例如：

- `tests/unit/test_cli.py` 仍大量导入 `claudeflow.runtime_manager`

因此 wrapper 是“待移除兼容层”，不是“可立即删除文件”。

### 3.3 `__init__.py` 仍在暴露大量遗留 API

当前包导出仍包含：

- `EmployeePool`
- `KnowledgeRetriever`
- `AlertHandler`
- `ProgressReporter`
- `WebSocketClient`
- `HaikuClient`
- `PhaseReviewer`
- `TaskReviewer`

如果不先收缩 `__init__.py`，物理删除实现文件会先把包接口打断。

### 3.4 `workflow/*` 与 `governance/*` 仍受测试覆盖

这些模块虽然不再是未来核心，但仍有大量单测、集成测试、E2E 在引用。  
删除它们的动作必须与测试清理同步进行。

## 4. 安全清理顺序

建议严格按以下顺序执行：

### 阶段 A：新服务成型

目标：

- 新建独立 runtime API 服务文件，例如 `src/claudeflow/runtime/api.py`

要求：

- 接管当前 `hermes_service.py` 中所有 runtime 和 session 相关端点
- 前端切换到新服务路径

### 阶段 B：导出层收缩

目标：

- 收缩 `src/claudeflow/__init__.py`

要求：

- 默认只导出当前核心 runtime API
- 历史模块不再作为主包公共接口暴露

### 阶段 C：兼容层移除

目标：

- 移除根目录 wrapper

要求：

- 先迁移所有测试与导入路径
- 再删除 wrapper 文件

### 阶段 D：遗留模块降级

目标：

- 对 `workflow/*`、`governance/*`、V2 辅助模块做二选一：
  - 迁入 `legacy/`
  - 或删除

要求：

- 必须先决定“归档保留”还是“完全移除”
- 不能边删边猜

### 阶段 E：删除 `hermes_service.py`

目标：

- 在新 runtime 服务和 session 服务完全替代后，删除 `hermes_service.py`

要求：

- 前端不再依赖 `/hermes/...`
- 测试已迁移

## 5. 不可直接删除项

以下项目在没有完成前置迁移前，不能直接删：

- `src/claudeflow/hermes_service.py`
- `src/claudeflow/__init__.py`
- `src/claudeflow/runtime_manager.py`
- `src/claudeflow/cli_driver.py`
- `src/claudeflow/checkpoint.py`
- `src/claudeflow/scheduler.py`
- `src/claudeflow/state_machine.py`
- `src/claudeflow/task_manager.py`
- `tests/unit/test_hermes_service.py`
- `tests/unit/test_cli.py`
- `tests/integration/test_hermes_cli_integration.py`
- `tests/integration/test_v3_integration.py`
- `tests/unit/governance/**`
- `tests/integration/test_python_websocket.py`

## 6. 推荐的最终目标结构

推荐未来目标不是“先删干净再说”，而是：

```text
src/claudeflow/
├── __init__.py
├── cli.py
├── runtime/
│   ├── __init__.py
│   ├── cli_driver.py
│   ├── manager.py
│   └── api.py
├── thinking_filter.py
├── session_parser.py
└── legacy/   # 若决定保留历史能力
```

## 7. 对执行模型的建议

如果另一个模型负责执行清理，应要求它遵守：

1. 不允许直接大面积删除历史模块。
2. 必须先迁移 API，再清理实现。
3. 每删一层都要先跑对应测试。
4. 所有清理动作必须同步更新文档。
5. 任何不确定是否为公共 API 的模块，先视为不能删。
