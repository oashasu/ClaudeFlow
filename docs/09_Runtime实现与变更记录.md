# Runtime实现与变更记录

> 目的：沉淀当前仓库里已经落地的 runtime / console 实现，并作为后续改动的固定记录入口。
>
> 规则：从 2026-04-24 起，任何对 runtime、Hermes API、Web Console 的功能性更新，都必须同步更新本文件或新增对应专题文档，并在提交中一并包含文档变更。

## 当前已实现范围

### 1. Runtime 多会话 PoC

已落地文件：

- `src/claudeflow/runtime/manager.py`
- `src/claudeflow/runtime/cli_driver.py`
- `src/claudeflow/cli.py`
- `examples/task-graph.schema.json`
- `examples/task-graph.sample.json`

当前能力：

- 初始化 `.claudeflow/` 运行时目录
- 以 `task_id -> session_id -> worktree` 形式维护 worker 会话
- 为写任务创建独立 `git worktree`
- 基于 `write_paths` 做逻辑锁，避免并发写冲突
- 支持 `runtime start / complete / fail / status / show`
- 支持 task graph 加载、最小 schema 校验、依赖判断
- 支持 `dispatch / plan / explain`
- 支持 `priority` 排序
- 支持 `max_concurrent` 并发槽位
- 支持 `reason_code + reason` 的稳定阻塞原因输出
- 支持 `--json` 输出，供脚本和前端消费

### 2. Runtime API（原 Hermes Runtime API，已迁移）

> ⚠️ hermes_service.py 即将在 Phase 6 删除。全部端点已由 runtime/api.py 接管。

已落地文件：

- `src/claudeflow/runtime/api.py`（新，接管全部端点）
- `src/claudeflow/hermes_service.py`（遗留，待删除）

当前能力（由 runtime/api.py 提供）：

- `GET /api/runtime/status`
- `GET /api/runtime/sessions`
- `GET /api/runtime/plan`
- `GET /api/runtime/explain/{task_id}`
- `POST /api/runtime/dispatch`
- `POST /api/runtime/task/{task_id}/complete`
- `POST /api/runtime/task/{task_id}/fail`
- `GET /api/session/{session_id}/events-list`
- `POST /api/session/{session_id}/intervene`
- `POST /api/session/start`（新增）
- `POST /api/session/{session_id}/cancel`（新增）
- `GET /api/session/{session_id}/events`（SSE，新增）
- `GET /api/session/{session_id}/status`（新增）
- `GET /health`（新增）

### 3. Runtime Console

已落地文件：

- `console/src/views/RuntimeConsole.vue`
- `console/src/services/runtimeApi.ts`
- `console/src/components/runtime/RuntimeMetricGrid.vue`
- `console/src/components/runtime/RuntimeReasonList.vue`
- `console/src/components/runtime/RuntimeExplainCard.vue`
- `console/src/components/runtime/RuntimeSessionTable.vue`
- `console/src/components/runtime/RuntimeSessionInspector.vue`

当前能力：

- 独立 `/runtime` 路由
- sample / live 双模式
- 读取 live `status / sessions / plan / explain / dispatch`
- 自动刷新和轮询间隔控制
- 展示 runnable / blocked / running / started
- 展示 `reason_code`
- session 列表动作：
  - `解释任务`
  - `查看事件`
  - `发送干预`
  - `标记完成`
  - `标记失败`
- session inspector：
  - 当前 session 摘要
  - 事件列表
  - 最近读取时间
  - 数据来源标记
  - 直接执行 intervene / complete / fail
- 与旧控制台的导航整合：
  - `Dashboard` 首页新增 Runtime 入口卡片
  - `TaskDetail` 顶部新增 Runtime 跳转入口

## 2026-04-24 Hermes 遗留清理记录

> 执行规格: [2026-04-24-hermes-legacy-cleanup-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-hermes-legacy-cleanup-spec.md)

### Phase 1: runtime/api.py 接管全部端点 ✅

- 新建 `src/claudeflow/runtime/api.py`，注册全部 18 条路由
- Session 端点：start, events(SSE), intervene, cancel, status, events-list
- Runtime 端点：plan, status, sessions, explain/{task_id}, dispatch, task/{task_id}/complete, task/{task_id}/fail
- CORS 配置：localhost:5173, localhost:3000, 192.168.100.181:5173
- 不再依赖 hermes_service.py，可独立 uvicorn 启动

### Phase 2: 前端切换到 runtime 服务路径 ✅

- `console/vite.config.ts`: 代理路径从 `/hermes` → `/runtime-api`
- `console/src/services/runtimeApi.ts`: RUNTIME_BASE 从 `/hermes/runtime` → `/runtime-api/runtime`，SESSION_BASE 同理
- `console/src/services/sse.ts`: HERMES_URL → RUNTIME_URL，注释更新
- `console/src/services/api.ts`: sessionApi 注释说明旧任务流页面走 Java 后端，Runtime Console 走 runtimeApi.ts

### Phase 3: 收缩 __init__.py 导出层 ✅

- 版本号 2.4.0 → 3.0.0
- 移除 13 个遗留符号导出：EmployeePool, Employee, EmployeeStatus, EmployeeRole, KnowledgeRetriever, KnowledgeEntry, AlertHandler, ProgressReporter, WebSocketClient, session_utils 函数, HaikuClient, HaikuConfig, PhaseReviewer, TaskReviewer
- 保留导出：Runtime 核心(7) + Workflow(8) + CliApp + ThinkingFilter + SessionParser
- 模块文件未删除，直接导入路径 `from claudeflow.xxx import ...` 仍然可用

### Phase 4: 兼容层 wrapper 清理 ✅

- 迁移 18 个文件的 import 路径到 `claudeflow.runtime.*` 和 `claudeflow.workflow.*`
- 迁移 14 个 `patch()` mock 路径到新路径
- 删除 6 个 wrapper 文件：
  - `src/claudeflow/cli_driver.py` → 直接用 `claudeflow.runtime.cli_driver`
  - `src/claudeflow/runtime_manager.py` → 直接用 `claudeflow.runtime.manager`
  - `src/claudeflow/checkpoint.py` → 直接用 `claudeflow.workflow.checkpoint`
  - `src/claudeflow/scheduler.py` → 直接用 `claudeflow.workflow.scheduler`
  - `src/claudeflow/state_machine.py` → 直接用 `claudeflow.workflow.state_machine`
  - `src/claudeflow/task_manager.py` → 直接用 `claudeflow.workflow.task_manager`
- 418 测试通过（排除 3 个预先存在的 numpy/mock 问题）

### Phase 5: 历史模块降级处理 ✅

**保留在根目录（core runtime/workflow 依赖）：**
- `workflow/*` — 核心模块，直接被 runtime 使用
- `alert_handler.py` — workflow/checkpoint.py 和 task_manager.py 条件导入
- `websocket_client.py` — alert_handler.py 依赖
- `session_utils.py` — websocket_client.py 内部使用
- `subtask_detector.py` — workflow/scheduler.py 依赖

**迁移到 `legacy/`（仅测试依赖，无生产代码使用）：**
- `governance/*` → `legacy/governance/`（V3 治理模块，需要 numpy）
- `haiku_client.py` → `legacy/haiku_client.py`（V2 异步复盘）
- `phase_reviewer.py` → `legacy/phase_reviewer.py`（V2 阶段复盘）
- `task_reviewer.py` → `legacy/task_reviewer.py`（V2 任务复盘）
- `knowledge_retrieval.py` → `legacy/knowledge_retrieval.py`（V1/V2 知识检索）
- `employee_pool.py` → `legacy/employee_pool.py`（V1/V2 员工池）
- `progress_reporter.py` → `legacy/progress_reporter.py`（仅测试依赖）

所有测试文件的 import 路径已更新到 `claudeflow.legacy.*`。418 测试通过。

### Phase 6: 删除 hermes_service.py ✅

- 删除 `src/claudeflow/hermes_service.py`（全部端点已由 runtime/api.py 接管）
- 同步删除测试：
  - `tests/unit/test_hermes_service.py`
  - `tests/integration/test_hermes_cli_integration.py`
- 395 测试通过（减少 23 个已删除的 hermes 测试，0 个新增失败）

## 2026-04-24 实现记录

### Runtime CLI / 调度层

- 新增 runtime manager，形成最小多会话执行内核
- 完成 `task graph`、`dispatch`、`plan`、`explain` 闭环
- 完成 `reason_code` 稳定化
- 完成 runtime schema / sample 输出

### Python 结构整理

- 将 Python 主线拆成 `runtime/` 与 `workflow/`
- 保留顶层兼容导出，避免旧导入路径直接失效
- 补充 `.gitignore`，隔离运行产物与缓存

### Runtime Console

- 新增独立 runtime 页面，不与旧 Dashboard/TaskDetail 混模
- 接入 live runtime API
- 页面从 JSON 编辑器风格收敛为结构化控制台
- 增加总览栏、自动刷新、session 列表、session inspector
- 增加 session 级操作入口，前端可直接触发 `intervene / complete / fail`
- 将 `Dashboard / TaskDetail` 做成入口层，只负责跳转到 Runtime Console，不混入 runtime 状态模型

## 待实现需求

### 2026-04-24 下一阶段 Runtime 优化规格

状态：`pending`

已拆分为月度路线图和 4 份独立规格文档：

- [2026-04-24-runtime-monthly-roadmap.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-runtime-monthly-roadmap.md)
- [2026-04-24-runtime-action-audit-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-runtime-action-audit-spec.md)
- [2026-04-24-runtime-console-refactor-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-runtime-console-refactor-spec.md)
- [2026-04-24-runtime-schema-validation-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-runtime-schema-validation-spec.md)
- [2026-04-24-runtime-scheduler-enhancement-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-runtime-scheduler-enhancement-spec.md)

### 2026-04-24 Hermes 遗留清理准备文档

状态：`pending`

已新增交接文档：

- [2026-04-24-hermes-legacy-cleanup-analysis.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-hermes-legacy-cleanup-analysis.md)
- [2026-04-24-hermes-legacy-cleanup-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-hermes-legacy-cleanup-spec.md)

用途：

- 为另一个执行模型提供清理边界
- 明确不可直接删除项
- 固定安全迁移顺序
- 为后续专项代码审查提供审查基线

### 2026-04-24 代码审查修复

状态：`done`

基于代码审查发现的 3 个问题已全部修复：

1. **sessionApi 路由断裂修复**：`api.ts` sessionApi 从 `/api/hermes/session/...` 改为 `/runtime-api/session/...`，通过 Vite 代理正确路由到 Python runtime 服务
2. **runtime 依赖补充**：`pyproject.toml` 新增 `fastapi>=0.100.0`, `uvicorn[standard]>=0.20.0`, `pydantic>=2.0.0`
3. **runtime API 测试覆盖**：新建 `tests/unit/test_runtime_api.py`（25 个测试），覆盖全部 14 条路由的健康检查、成功/失败/404 场景。同步修复 `test_v3_integration.py` 中 stale import（hermes_service → runtime.api）

### 2026-04-24 Hermes 清理代码审查结论

状态：`reviewed`

结论：

- 本轮 Hermes 遗留清理相关主路径未发现阻塞合并的问题
- 上一轮审查指出的 3 个关键问题已全部修复：
  1. 旧任务流 `sessionApi` 已切到 `/runtime-api/session/...`
  2. `runtime/api.py` 所需依赖已补入 `pyproject.toml`
  3. `runtime/api.py` 已补充替代性单测，旧 `hermes_service` 的 stale import 已清理

本次审查重点：

- 检查旧 `/hermes/session` 路径是否残留在前端主路径
- 检查 `runtime/api.py` 的依赖声明是否完整
- 检查 `test_runtime_api.py` 是否覆盖 runtime + session 主端点
- 检查 `test_v3_integration.py` 是否仍引用已删除的 `hermes_service.py`

验证结果：

- `pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/integration/test_v3_integration.py`
  - 结果：`74 passed, 1 skipped`
- `npm test -- --run`
  - 结果：`8 files, 41 tests passed`

剩余风险：

- `tests/integration/test_v3_integration.py` 中 runtime API smoke test 仍为跳过状态，不算真正运行的集成验证
- 这次审查只覆盖 Hermes 清理相关主路径，不包含工作树中其他与本次主题无关的未提交改动

## 约束

后续每次涉及以下范围的功能变更，必须同步更新文档：

- `src/claudeflow/runtime/**`
- `src/claudeflow/workflow/**`
- `console/src/views/RuntimeConsole.vue`
- `console/src/components/runtime/**`
- `console/src/services/runtimeApi.ts`
- `examples/runtime-*.schema.json`
- `examples/task-graph*.json`

建议执行方式：

1. 代码改动完成
2. 更新本文件中的“当前已实现范围”或追加新的日期记录
3. 如涉及协议或对象结构变化，同时更新 `examples/*.schema.json`
4. 测试通过后再提交 Git

## 下一步建议

- 优先按 [2026-04-24-runtime-action-audit-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-runtime-action-audit-spec.md) 推进 P0：操作确认与审计
- 实现时按月度路线图分批推进，而不是一次性并行开做
- session 事件查看后续继续收敛成可过滤、可分页、可定位工具调用的视图
