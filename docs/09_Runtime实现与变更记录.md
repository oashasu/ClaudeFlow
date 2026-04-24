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

### 2. Hermes Runtime API

已落地文件：

- `src/claudeflow/hermes_service.py`

当前能力：

- `GET /api/runtime/status`
- `GET /api/runtime/sessions`
- `GET /api/runtime/plan`
- `GET /api/runtime/explain/{task_id}`
- `POST /api/runtime/dispatch`
- `POST /api/runtime/task/{task_id}/complete`
- `POST /api/runtime/task/{task_id}/fail`
- `GET /api/session/{session_id}/events-list`
- `POST /api/session/{session_id}/intervene`

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

## 约束

后续每次涉及以下范围的功能变更，必须同步更新文档：

- `src/claudeflow/runtime/**`
- `src/claudeflow/hermes_service.py`
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

- 为 session 级动作补充确认机制和操作审计
- 为 runtime JSON 返回体补更严格的接口 schema 校验
- 将 session 事件查看进一步收敛成可过滤、可分页、可定位工具调用的视图
