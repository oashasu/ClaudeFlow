# ClaudeFlow 系统索引

> 最后更新：2026-04-28
> 项目位置：`/Users/claw/sandbox/personal/claudeflow/`
> **服务目录**: `~/services/claudeflow/` (纯运行场景)

文档导航入口：[docs/README.md](README.md)

---

## 目录说明

| 目录 | 用途 | 说明 |
|------|------|------|
| `~/sandbox/personal/claudeflow/` | 开发目录 | 用于开发、测试、迭代 |
| `~/services/claudeflow/` | 服务目录 | 用于生产运行，与开发隔离 |

**服务隔离原则**: 开发过程中的变更不会自动同步到服务目录。
服务目录仅通过 `git pull` 更新稳定版本，确保运行稳定。

---

## 当前版本：Runtime V3（v3.3）

ClaudeFlow 是一个任务调度管理系统，通过 Runtime 多会话内核调度 Claude Code CLI 执行具体任务。当前主线为 Runtime V3，V1/V2 的设计已沉淀到实现中或降级到 `legacy/`。

### 核心模块

| 模块 | 职责 | 路径 |
|------|------|------|
| Runtime Manager | 多会话生命周期管理 | `src/claudeflow/runtime/manager.py` |
| Runtime CLI Driver | CLI 进程驱动与会话追踪 | `src/claudeflow/runtime/cli_driver.py` |
| Runtime API | FastAPI 路由层（18 条端点） | `src/claudeflow/runtime/api.py` |
| CLI 入口 | 命令行工具 | `src/claudeflow/cli.py` |
| Workflow Engine | 状态机 / 调度器 / 任务管理 | `src/claudeflow/workflow/` |
| Runtime Console | Vue 前端控制台 | `console/src/views/RuntimeConsole.vue` |

### Runtime 能力

- `runtime start / complete / fail / status / show`
- `runtime dispatch / plan / explain`
- `priority` 排序、`max_concurrent` 并发槽位
- `reason_code + reason` 稳定阻塞原因输出
- `--json` 输出供脚本和前端消费
- task graph 加载、schema 校验、依赖判断
- 独立 git worktree 隔离
- `write_paths` 逻辑锁防并发写冲突
- SSE 实时事件推送

### Runtime API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/runtime/status` | GET | 全局状态 |
| `/api/runtime/sessions` | GET | 会话列表 |
| `/api/runtime/plan` | GET | 执行计划 |
| `/api/runtime/explain/{task_id}` | GET | 任务解释 |
| `/api/runtime/dispatch` | POST | 调度任务 |
| `/api/runtime/task/{task_id}/complete` | POST | 标记完成 |
| `/api/runtime/task/{task_id}/fail` | POST | 标记失败 |
| `/api/session/start` | POST | 启动会话 |
| `/api/session/{id}/events` | GET (SSE) | 事件流 |
| `/api/session/{id}/events-list` | GET | 事件列表 |
| `/api/session/{id}/intervene` | POST | 注入干预 |
| `/api/session/{id}/cancel` | POST | 取消会话 |
| `/api/session/{id}/status` | GET | 会话状态 |
| `/health` | GET | 健康检查 |

### Runtime Console

独立 `/runtime` 路由，sample / live 双模式，支持：

- 总览栏：runnable / blocked / running / started 统计
- session 列表：解释任务 / 查看事件 / 发送干预 / 标记完成 / 标记失败
- session inspector：当前摘要 / 事件列表 / 直接操作
- 自动刷新与轮询间隔控制
- Dashboard 首页 Runtime 入口卡片、TaskDetail Runtime 跳转入口
- **Phase 3 新增**:
  - 结构拆分：types / validators / composables / components
  - 高影响动作确认对话框（intervene/complete/fail）
  - 审计记录查询与展示
  - 协议校验与 parseError 显示
- **Phase 4 新增**:
  - 测试 harness 标准化（withComposable, flushPromises, mock 基座）
  - parse/validate 错误路径稳定断言
  - Smoke 入口真实可运行（status/sessions/events/dispatch/audit）

### 测试与可观测性

测试入口、mock 约定、smoke 入口、排障顺序详见 [runtime/testing-observability.md](runtime/testing-observability.md)。

| 层级 | 入口 | 命令 |
|------|------|------|
| 前端单元 | Vitest | `cd console && npm test` |
| Python 单元 | pytest | `PYTHONPATH=src python3 -m pytest tests/unit/` |
| Smoke 入口 | Python | `PYTHONPATH=src python3 scripts/runtime_smoke.py` |

### Java HTTP 消费层

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/runtime-consume/status` | GET | Runtime 状态代理 |
| `/api/runtime-consume/sessions` | GET | Runtime sessions 代理 |
| `/api/runtime-consume/plan` | GET | Runtime plan 代理 |
| `/api/runtime-consume/explain/{taskId}` | GET | 任务解释代理 |
| `/api/runtime-consume/audit` | GET | 审计记录代理 |

边界约定见 [runtime/java-http-boundary.md](runtime/java-http-boundary.md)。

---

## 文档导航

| 分类 | 目录 | 说明 |
|------|------|------|
| 核心 | [runtime/](runtime/) | 变更记录 + 测试与可观测性 |
| 运维 | [operations/](operations/) | 操作手册、部署指南 |
| 历史 | [archive/](archive/) | V1/V2 早期设计文档 |
| 规格 | [specs/](specs/) | 功能规格与路线图 |
| 扩展 | [superpowers/](superpowers/) | Token 治理、Console 等专题设计 |

核心文档：
- [runtime/changelog.md](runtime/changelog.md) - 实现变更记录
- [runtime/testing-observability.md](runtime/testing-observability.md) - 测试入口、mock 约定、排障顺序
- [runtime/java-http-boundary.md](runtime/java-http-boundary.md) - Java HTTP 消费层契约

完整索引见 [docs/README.md](README.md)。

---

## 架构演进历史

| 版本 | 时间 | 核心变化 | 一行描述 |
|------|------|----------|----------|
| V1 | 2026-04-19 | 七状态模型 + CLI + 流程调度 + TDD 验证 | 最小可用版本，验证核心调度可行性 |
| V2.0 | 2026-04-19 | WebSocket/SSE 通信 + Agent 提炼 + Phase0 拆分 + 异步复盘 | 扩展通信与提炼能力 |
| V2.2 | 2026-04-21 | Spring Boot + Vue Web Console | Web 控制台版本 |
| V2.3 | 2026-04-22 | Haiku 异步复盘模块 + SSE 稳定性 | 310 测试通过，88% 覆盖率 |
| V2.4 | 2026-04-22 | CLI 驱动模块 + 指令集注入整合 | 379 测试，96% 覆盖率 |
| V3.0 | 2026-04-24 | Runtime 多会话内核 + task graph + dispatch + Hermes 全面清理 | 当前主线，runtime/api.py 接管全部端点 |
| V3.1 | 2026-04-27 | Console 结构收口 + 动作确认链 + 审计 + schema校验 + Java消费契约 | Phase 3 验收完成，A31-A35 全部通过 |
| V3.2 | 2026-04-27 | Testing harness 标准化 + parse/validate 错误路径 + Smoke 入口 + 文档同步 | Phase 4 验收完成，A41-A46 全部通过 |
| V3.3 | 2026-04-28 | Release checklist + Quality gate 固化 + 统一交付口径 + 发布后验证 | Phase 5 已完成，release-readiness 分层与回滚契约落地 |

V1/V2 的设计文档归档在 [archive/](archive/)，仅供参考。实现状态以 [runtime/changelog.md](runtime/changelog.md) 为准。

---

## 下一步

参见 [specs/2026-04-24-runtime-monthly-roadmap.md](specs/2026-04-24-runtime-monthly-roadmap.md)。
