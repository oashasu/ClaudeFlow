# Hermes 遗留清理与 Runtime 核心收敛规格

> 状态：`pending`
>
> 优先级：`P0`
>
> 依赖文档：[2026-04-24-hermes-legacy-cleanup-analysis.md](2026-04-24-hermes-legacy-cleanup-analysis.md)

## 1. 目标

将当前仓库从“runtime-poc + Hermes/V1/V2/V3 并存”收敛为“runtime 为主、历史模块退出主路径”的结构，同时避免误删现有前端、测试和包导出仍依赖的能力。

## 2. 范围

本规格覆盖：

- runtime API / session API 迁移
- `hermes_service.py` 退场
- `__init__.py` 导出收缩
- wrapper 清理
- 历史模块降级或删除
- 测试和文档同步

## 3. 分阶段要求

### 阶段 1：建立新 runtime 服务入口

要求：

- 新建独立 runtime 服务文件，例如 `src/claudeflow/runtime/api.py`
- 接管以下端点：
  - runtime 相关端点
  - session 相关端点

至少应覆盖：

- `GET /api/runtime/status`
- `GET /api/runtime/sessions`
- `GET /api/runtime/plan`
- `GET /api/runtime/explain/{task_id}`
- `POST /api/runtime/dispatch`
- `POST /api/runtime/task/{task_id}/complete`
- `POST /api/runtime/task/{task_id}/fail`
- `GET /api/session/{session_id}/events-list`
- `POST /api/session/{session_id}/intervene`

### 阶段 2：前端切换

要求：

- Runtime Console 和旧任务流中所有 session/runtime 请求全部切到新服务入口
- 不再依赖旧的 Hermes 服务命名作为主要入口

### 阶段 3：导出层收缩

要求：

- 收缩 `src/claudeflow/__init__.py`
- 默认只保留 runtime 主线的公共导出
- 历史模块不得继续作为默认公共 API 暴露

### 阶段 4：兼容层清理

要求：

- 迁移完导入路径后，删除 wrapper 文件
- 删除前必须确认测试已改到新路径

### 阶段 5：历史模块处理

要求：

以下模块必须明确做出决策：

- 删除
- 或迁入 `legacy/`

待决策范围：

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

### 阶段 6：删除 Hermes 服务

前提：

- 前端与测试都已迁到新 runtime 服务
- session/runtime 端点不再由 `hermes_service.py` 提供

完成后：

- 删除 `src/claudeflow/hermes_service.py`

## 4. 非目标

- 不在本阶段重构旧 Java/Spring 控制台后端
- 不在本阶段重写所有历史设计文档
- 不在本阶段保留 Hermes 作为新的运行时命名中心

## 5. 严格验收标准

### 5.1 API 验收

1. 新 runtime 服务必须完整承接 runtime + session 端点，而不是只迁 runtime 半套。
2. 前端所有 runtime/session 调用不再依赖 `hermes_service.py`。
3. 迁移后 Runtime Console 的以下能力不能回退：
   - 查看 status
   - 查看 sessions
   - explain
   - dispatch
   - 查看 session events
   - intervene
   - complete
   - fail

### 5.2 包结构验收

1. `src/claudeflow/__init__.py` 中不得继续默认导出明显属于历史主线的模块。
2. 根目录 wrapper 删除后，测试和 CLI 不得再依赖旧导入路径。
3. `hermes_service.py` 删除前，仓库内不应再存在前端或测试对其作为主服务入口的依赖。

### 5.3 测试验收

1. 与 runtime 当前主线直接相关的测试必须通过。
2. 被删除模块对应测试要么迁移，要么同步删除，不允许留下失效测试。
3. 任何阶段都不允许通过“跳过主线测试”来完成清理。

### 5.4 文档验收

1. 每个清理阶段完成后，必须更新：
   - [09_Runtime实现与变更记录.md](../09_Runtime实现与变更记录.md)
   - [INDEX.md](../INDEX.md)
2. 若新增 `legacy/`，必须写清楚哪些模块被降级而非删除。

## 6. 执行顺序约束

必须遵循：

1. 先新建服务
2. 再切前端
3. 再收缩导出
4. 再删 wrapper
5. 再处理历史模块
6. 最后删 `hermes_service.py`

不允许反过来做。

## 7. 面向执行模型的明确要求

如果由另一个模型执行本规格，必须遵守：

1. 先读分析文档，再动代码。
2. 每删除一个层次前，先列出受影响文件。
3. 不确定是否仍被依赖的模块，一律先保守处理。
4. 完成后必须提供：
   - 改动摘要
   - 删除清单
   - 保留清单
   - 测试结果

## 8. 后续审查要求

本规格执行完成后，需要做一次专门代码审查，重点检查：

- 是否存在误删公共 API
- 是否存在前端残留对旧 Hermes 路径的依赖
- 是否存在测试覆盖空洞
- 是否存在“功能没迁完就删旧模块”的问题
