# ClaudeFlow 文档中心

> 最后更新：2026-04-25

本目录是 ClaudeFlow 项目的完整文档集。项目已从早期的 V1/V2 设计演进到 Runtime V3 架构，文档已按用途重新组织。

---

## 目录结构

```
docs/
├── runtime/          Runtime V3 核心——架构、变更记录
├── operations/       运维与使用——操作手册、部署指南
├── archive/          历史设计文档——V1/V2 早期设计，仅供参考
│   ├── v1/           V1 阶段文档
│   ├── v2/           V2 阶段设计（01~07）
│   └── legacy/       V3 早期设计（08）
├── specs/            规格文档——待实现的功能规格与路线图
└── superpowers/      扩展设计——Token 治理、Web Console 等专题
```

| 目录 | 说明 |
|------|------|
| `runtime/` | Runtime V3 变更记录（持续更新） |
| `operations/` | 面向使用者的操作手册：环境搭建、启动命令、Console 使用、部署发布 |
| `archive/` | V1/V2 早期设计文档（通信层、Agent 提炼、前置拆分等），这些设计已沉淀到 Runtime 或降级到 legacy，仅供历史追溯 |
| `specs/` | 功能规格文档，按日期命名，包含路线图、优化规格、清理规格等 |
| `superpowers/` | 独立专题设计（Agent Token 治理、Web Console 设计、实现计划等） |

---

## 文档索引

### runtime/（Runtime V3 核心）

| 文档 | 说明 |
|------|------|
| [changelog.md](runtime/changelog.md) | Runtime 实现与变更记录（持续更新） |

后续待补充：
- `architecture.md` — Runtime 多会话架构：manager、cli_driver、调度层、reason_code
- `api-reference.md` — Runtime API 参考：全部 18 条路由及请求/响应格式
- `cli-reference.md` — CLI 命令手册：start / complete / fail / dispatch / plan / explain
- `data-model.md` — 数据模型：task graph schema、session 模型、checkpoint 结构

### operations/（运维与使用）

| 文档 | 说明 |
|------|------|
| [user-manual.md](operations/user-manual.md) | 操作手册：环境搭建、启动流程、Console 使用、部署发布 |

### archive/（历史设计）

| 原编号 | 文件 | 说明 |
|--------|------|------|
| — | [README_V1.md](archive/v1/README_V1.md) | V1 分支需求与设计 |
| — | [v1_development_prompt.md](archive/v1/v1_development_prompt.md) | V1 开发任务 prompt |
| 01 | [通信层设计](archive/v2/01_通信层设计.md) | V2：WebSocket + SSE 通信层 |
| 02 | [Agent提炼机制设计](archive/v2/02_Agent提炼机制设计.md) | V2：分层提炼防止死循环刷屏 |
| 03 | [前置拆分流程设计](archive/v2/03_前置拆分流程设计.md) | V2：Phase0 拆分缓解上下文膨胀 |
| 04 | [强制checkpoint机制设计](archive/v2/04_强制checkpoint机制设计.md) | V2：阻塞式注入 checkpoint |
| 05 | [子Agent异步总结设计](archive/v2/05_子Agent异步总结设计.md) | V2：Haiku 异步复盘 |
| 06 | [Claude Code输出格式规范](archive/v2/06_Claude_Code输出格式规范.md) | V2：事件解析规范 |
| 07 | [V2设计问题清单](archive/v2/07_V2设计问题清单.md) | V2：设计审查问题 |
| 08 | [V3 Checkpoint版本快照优化](archive/legacy/08_V3_Checkpoint版本快照优化.md) | V3：Git 绑定 + 文件边界快照 |

### specs/（功能规格）

| 文档 | 状态 | 说明 |
|------|------|------|
| [runtime-monthly-roadmap](specs/2026-04-24-runtime-monthly-roadmap.md) | active | 月度路线图 |
| [runtime-action-audit-spec](specs/2026-04-24-runtime-action-audit-spec.md) | pending | P0：操作确认与审计 |
| [runtime-console-refactor-spec](specs/2026-04-24-runtime-console-refactor-spec.md) | pending | Console 重构规格 |
| [runtime-scheduler-enhancement-spec](specs/2026-04-24-runtime-scheduler-enhancement-spec.md) | pending | 调度层增强规格 |
| [runtime-schema-validation-spec](specs/2026-04-24-runtime-schema-validation-spec.md) | pending | Schema 校验规格 |
| [hermes-legacy-cleanup-analysis](specs/2026-04-24-hermes-legacy-cleanup-analysis.md) | done | Hermes 清理分析 |
| [hermes-legacy-cleanup-spec](specs/2026-04-24-hermes-legacy-cleanup-spec.md) | done | Hermes 清理规格 |

### superpowers/（扩展设计）

| 文档 | 说明 |
|------|------|
| [Agent Token 治理设计](superpowers/specs/2026-04-21-agent-token-governance-design.md) | 五层治理：熔断 + 快照 + 验收 + 工具限流 + 恢复 |
| [Web Console V2.2.0 设计](superpowers/specs/2026-04-20-v2.2.0-web-console-design.md) | 控制台完整设计 |
| [V2.2.0 实现计划](superpowers/specs/2026-04-20-v2.2.0-implementation-plan.md) | 实现步骤 |

---

## 新读者阅读建议

**快速上手**（想立刻使用 ClaudeFlow）：

1. [operations/user-manual.md](operations/user-manual.md) — 搭建环境、启动服务
2. 项目根 [README.md](../README.md) — Runtime CLI 命令示例
3. [runtime/changelog.md](runtime/changelog.md) — 已实现功能一览

**理解架构**（想参与开发）：

1. [INDEX.md](INDEX.md) — 系统设计总览、核心模块、API 端点
2. [runtime/changelog.md](runtime/changelog.md) — 变更历史
3. [specs/2026-04-24-runtime-monthly-roadmap.md](specs/2026-04-24-runtime-monthly-roadmap.md) — 后续规划

**历史溯源**（想了解设计演进）：

1. [INDEX.md](INDEX.md) 的「架构演进历史」章节
2. 按 archive/v2/ 中 01-07 的编号顺序阅读
3. 注意：这些是早期设计，实现状态以 runtime/changelog.md 为准
