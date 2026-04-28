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

## 2026-04-25 文档体系重构

### 变更概要

将 `docs/` 目录从扁平编号式组织改为按用途分类的目录结构，以 Runtime V3 为文档中心，V1/V2 历史设计归档。

### 变更原因

1. `docs/` 目录原有 10+ 个编号文件（01-10）混合了 V1、V2、V3 三个版本的内容，新读者无法快速定位当前有效信息
2. V1/V2 的设计已沉淀到 Runtime V3 实现或降级到 `legacy/` 代码，对应的设计文档只保留历史参考价值
3. Runtime V3 已是主线（v3.0.0），文档组织需要反映这一事实
4. 新增文档需要一个明确的归位规则，避免再次积累到根目录

### 目录结构调整

```
docs/
├── README.md                 ← 新增：文档导航入口
├── INDEX.md                  ← 改造：以 Runtime V3 为中心
├── runtime/                  ← 新增目录
│   └── changelog.md              ← 本文件（从 09 搬迁）
├── operations/               ← 新增目录
│   └── user-manual.md            ← 从 10 搬迁
├── archive/                  ← 新增目录
│   ├── v1/                       ← V1 文档归档
│   │   ├── README_V1.md
│   │   └── v1_development_prompt.md
│   ├── v2/                       ← V2 设计文档归档（01~07）
│   │   ├── 01_通信层设计.md
│   │   ├── 02_Agent提炼机制设计.md
│   │   ├── 03_前置拆分流程设计.md
│   │   ├── 04_强制checkpoint机制设计.md
│   │   ├── 05_子Agent异步总结设计.md
│   │   ├── 06_Claude_Code输出格式规范.md
│   │   └── 07_V2设计问题清单.md
│   ├── legacy/                   ← V3 早期设计归档
│   │   └── 08_V3_Checkpoint版本快照优化.md
│   └── checkpoint/               ← 设计 checkpoint JSON
│       └── v14_v2_design_start.json
├── specs/                    ← 保持不变
└── superpowers/              ← 保持不变
```

### 文件搬迁清单

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `docs/09_Runtime实现与变更记录.md` | `docs/runtime/changelog.md` | 本文件 |
| `docs/10_ClaudeFlow操作手册.md` | `docs/operations/user-manual.md` | 操作手册 |
| `docs/01~07_*.md` | `docs/archive/v2/` | V2 设计归档 |
| `docs/08_V3_Checkpoint版本快照优化.md` | `docs/archive/legacy/` | V3 早期设计归档 |
| `docs/README_V1.md` | `docs/archive/v1/` | V1 文档归档 |
| `docs/v1_development_prompt.md` | `docs/archive/v1/` | V1 开发提示归档 |
| `docs/checkpoint/` | `docs/archive/checkpoint/` | checkpoint JSON 归档 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/README.md` | 文档导航入口，含目录说明、文档索引、阅读建议 |
| `docs/runtime/` | Runtime V3 核心文档目录 |
| `docs/operations/` | 运维与使用文档目录 |
| `docs/archive/` | 历史设计文档归档目录 |

### 文档放置规则（面向其他模型）

后续新增文档按以下规则放置：

| 文档类型 | 放置目录 | 命名规则 |
|----------|----------|----------|
| Runtime 架构/API/CLI/数据模型文档 | `docs/runtime/` | 描述性英文名称 |
| Runtime 实现记录 | 追加到本文件（`docs/runtime/changelog.md`） | 日期 + 小节标题 |
| 操作手册、部署指南 | `docs/operations/` | 描述性英文名称 |
| 功能规格、优化规格 | `docs/specs/` | `YYYY-MM-DD-主题-spec.md` |
| 独立专题设计 | `docs/superpowers/` | `specs/YYYY-MM-DD-主题-design.md` |
| 已过时的设计文档 | `docs/archive/` | 保持原文件名 |

**禁止**：不再使用编号前缀（01_、02_...）命名新文档。
**禁止**：不再将新文档直接放到 `docs/` 根目录，必须归入对应子目录。

---

## 2026-04-27 Phase 3 Runtime Console 收口与治理链

> Phase 3 目标：Runtime Console 结构重构 + 高影响动作确认 + schema 校验 + Java 消费契约

### T301 Runtime Console 结构收口 (A31) ✅

**变更文件**:
- `console/src/types/runtime.ts` — Runtime 类型定义集中
- `console/src/validators/runtime.ts` — 协议校验函数
- `console/src/composables/useRuntimeLiveData.ts` — 状态获取主链
- `console/src/composables/useRuntimeActions.ts` — 动作执行主链
- `console/src/components/runtime/RuntimeActionConfirm.vue` — 确认对话框组件
- `console/src/components/runtime/RuntimeActionAudit.vue` — 审计展示组件
- `console/src/views/RuntimeConsole.vue` — 页面结构收口

**能力**:
- RuntimeConsole.vue 不再堆叠主要拉数和动作逻辑
- 页面主职责收敛为组件编排与状态绑定
- 结构拆分：types / validators / composables / components

### T302 高影响动作确认与审计链 (A32, A33) ✅

**变更文件**:
- `src/claudeflow/runtime/action_audit.py` — ActionAuditRecord 模型与写入器
- `src/claudeflow/runtime/api.py` — intervene/complete/fail 端点审计写入
- `console/src/services/runtimeApi.ts` — 前端调用审计查询 API
- `console/src/composables/useRuntimeActions.ts` — 动作结果审计反馈

**能力**:
- `complete` 与 `fail` 提交前需确认对话框
- `intervene` 提交前可见目标 task_id/session_id/prompt 摘要
- 所有高影响动作成功/失败后写入审计记录
- Console 可查询最近动作结果与错误信息

### T303 Runtime 协议校验闭环 (A34) ✅

**变更文件**:
- `examples/runtime-status.schema.json` — Status 协议固化
- `examples/runtime-sessions.schema.json` — Sessions 协议固化
- `examples/runtime-events.schema.json` — Events 协议固化
- `console/src/validators/runtime.ts` — parseStatus/parseSessions/parseSessionEvents
- `console/src/composables/useRuntimeLiveData.ts` — live payload 必经 parse
- `console/tests/runtimeValidator.spec.ts` — validator 单测
- `console/tests/runtimeLiveDataValidation.spec.ts` — live validation 单测
- `tests/unit/test_runtime_schema.py` — Python schema 校验单测

**能力**:
- status/sessions/events 有稳定 schema 约束
- live payload parse 失败时前端显示结构化错误
- validator 增强对 snake_case 字段兼容

### T304 Java HTTP 控制层消费契约 (A35) ✅

**变更文件**:
- `src/main/java/com/claudeflow/client/RuntimeClient.java` — Runtime API 消费客户端
- `src/main/java/com/claudeflow/controller/RuntimeController.java` — HTTP 端点代理
- `src/main/java/com/claudeflow/config/AppConfig.java` — RestTemplate 配置
- `src/test/java/com/claudeflow/client/RuntimeClientTest.java` — 客户端单测
- `src/test/java/com/claudeflow/controller/RuntimeControllerTest.java` — 控制器单测
- `docs/runtime/java-http-boundary.md` — 边界划分文档

**能力**:
- TaskController (/api/tasks) 旧任务流 CRUD
- RuntimeController (/api/runtime-consume) Runtime API 代理
- RuntimeClient vs HermesClient 区分（runtime级 vs session级）
- DTO 字段与 Python schema 对齐（snake_case → camelCase）
- Java 8 兼容（Collections.emptyList/Collectors.toList）

### 约束更新

Phase 3 新增约束文件：

- `docs/runtime/java-http-boundary.md` — Java/Python 边界约定

---

## 2026-04-27 Phase 4: Testing & Observability 收口

> 目标：前端测试 warning 清理 + harness 标准化 + smoke 入口 + 文档同步

### T401 前端测试 Harness 标准化 (A42) ✅

**变更文件**:
- `console/tests/helpers/runtimeMockSamples.ts` — 独立 sample 数据模块
- `console/tests/helpers/runtimeHarness.ts` — flushPromises/mountRuntimeConsole/withComposable
- `console/tests/runtimeLiveDataValidation.spec.ts` — 使用共享基座
- `console/tests/RuntimeConsole.spec.ts` — 导入共享 helpers，删除本地定义

**能力**:
- composable 测试在 Vue setup 上下文运行（无 lifecycle warning）
- vi.mock hoisting 正确配置（factory 内联数据 + beforeEach 配置导入 samples）
- RuntimeConsole.spec.ts 无本地 helper 函数定义

### T402 Action Audit 测试隔离 (A41/A43) ✅

**变更文件**:
- `console/tests/runtimeActionAudit.spec.ts` — 新增 10 tests

**能力**:
- 成功/空数据/失败路径稳定断言
- useRuntimeActions loadActionHistory 隔离测试
- RuntimeConsole.spec.ts 正确 mock listActionAudit 不产生 warning

### T403 Live Data Parse/Validate 错误路径 (A42/A43) ✅

**变更文件**:
- `console/tests/runtimeLiveDataValidation.spec.ts` — 扩展到 30 tests

**能力**:
- parsePlan/parseExplain/parseDispatch computed 错误路径断言
- loadLivePlan/loadLiveExplain/runLiveDispatch API + parse 失败路径
- Vue computed 惰性触发处理（先访问 .value，再检查 parseError）
- 不静默降级，无效 payload 返回 null + parseError 明确设置

### T404 Runtime Smoke 入口 (A44) ✅

**变更文件**:
- `scripts/runtime_smoke.py` — 新增 smoke 入口脚本

**能力**:
- FastAPI TestClient 验证 7 端点（status/sessions/events-list/plan/dispatch/action-audit/health）
- 真实可运行脚本，exit code 0/1
- events-list 使用 mock CliSession 验证真实 API 响应结构
- action-audit 写入 smoke_test 记录验证读写闭环

### T405 Testing/Observability 文档同步 (A45) ✅

**变更文件**:
- `docs/runtime/testing-observability.md` — 新增测试与可观测性指南
- `docs/INDEX.md` — 添加 Phase 4 能力描述 + testing-observability 文档链接

**能力**:
- 测试入口总览（前端 Vitest + Python pytest + Smoke 入口）
- Mock 约定（runtimeHarness + vi.mock hoisting）
- 排障顺序（lifecycle warning + mock 配置 + computed 惰性触发）
- Phase 3/4 已收口 warning（A41/A42/A43）

### 约束更新

Phase 4 新增文档：

- `docs/runtime/testing-observability.md` — 测试与可观测性指南

---

## 2026-04-28 Phase 5: Release Checklist & Quality Gate 收口

> 目标：release checklist 固化 + quality gate 分层 + 统一交付口径 + 发布后验证与回滚契约

### T501 Release Checklist & Gate Matrix (P51) ✅

**变更文件**:
- `docs/operations/release-checklist.md` — 发布检查清单
- `docs/operations/release-gate-matrix.md` — Gate 1-6 检查矩阵
- `scripts/verify-doc-consistency.sh` — Gate 6 文档一致性验证

**能力**:
- Gate 1-6 分层：test pass → lint clean → schema valid → smoke pass → quality gate → doc consistent
- Release checklist 与 quality gate matrix 固化
- INDEX.md / changelog.md / pipeline-state.json 三方一致性检查

### T502 Unified Release Gate Entry (P52) ✅

**变更文件**:
- `scripts/run-release-gates.sh` — Gate 1-6 统一入口脚本
- `docs/operations/release-gate-matrix.md` — gate 执行说明

**能力**:
- 单入口执行全部 gate 检查
- 返回 JSON 结构化结果（gate_status / passed_gates / failed_gates）
- PYTHONPATH=src 统一 Python 命令口径

### T503 Release Readiness Classification (P53) ✅

**变更文件**:
- `docs/operations/release-readiness.md` — release-ready / warning-budget / blocker 分层
- `docs/operations/release-checklist.md` — readiness 检查项

**能力**:
- release-ready: 全部 gate passed
- warning-budget: 允许非阻塞警告上限
- blocker: 必须修复的阻塞项（Gate 6 doc consistency 当前唯一 blocker）

### T504 Post-Release Verification (P54) ✅

**变更文件**:
- `docs/operations/post-release-verification.md` — 发布后验证流程
- 治理入口验证命令：PYTHONPATH=src python3 -c "from claudeflow.cli import main..."

**能力**:
- 发布后 runtime dispatch 验证命令
- Governance 入口：--governance-root .super-dev --phase-id phase-5
- JSON 结构化输出验证

### T505 Rollback Contract & Delivery Summary (P54) ✅

**变更文件**:
- `docs/operations/rollback-contract.md` — 回滚操作契约
- `docs/operations/delivery-summary-template.md` — 交付总结模板

**能力**:
- git revert HEAD 回滚命令
- Gate 5 失败日志 /tmp/gate5.log 定位
- PYTHONPATH=src 统一交付口径

### T506 Regression Verification & Acceptance Coverage (P51-P54) ✅

**验证范围**:
- 637 unit tests passed (tests/unit/)
- 7 smoke endpoints passed (scripts/runtime_smoke.py)
- Gate 6 doc consistency check（当前唯一 blocker）

**Acceptance Coverage**:
- A51: release checklist 覆盖 ✅
- A52: Gate 1-6 统一入口 ✅
- A53: release-readiness 分层 ✅
- A54: 发布后验证命令 ✅
- A55: 回滚契约与交付模板 ✅
- A56: 回归验证 + acceptance summary ✅

### 约束更新

Phase 5 新增文档：

- `docs/operations/release-checklist.md` — 发布检查清单
- `docs/operations/release-gate-matrix.md` — Gate 1-6 检查矩阵
- `docs/operations/release-readiness.md` — Release readiness 分层
- `docs/operations/post-release-verification.md` — 发布后验证
- `docs/operations/rollback-contract.md` — 回滚契约
- `docs/operations/delivery-summary-template.md` — 交付总结模板

---

## 下一步建议

- 优先按 [2026-04-24-runtime-action-audit-spec.md](/Users/claw/sandbox/personal/claudeflow/docs/specs/2026-04-24-runtime-action-audit-spec.md) 推进 P0：操作确认与审计
- 实现时按月度路线图分批推进，而不是一次性并行开做
- session 事件查看后续继续收敛成可过滤、可分页、可定位工具调用的视图
