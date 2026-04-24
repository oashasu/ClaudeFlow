# ClaudeFlow系统设计

> **日期**: 2026-04-19
> **项目位置**: `/Users/claw/sandbox/personal/claudeflow/`

---

## 分阶段开发策略

**核心原则**：不一次性做全，分阶段实现

```
V1（最小版本）→ 验证核心功能 + TDD流程可行性
    ↓
V2（扩展版本）→ 在V1基础上添加通信层/提炼机制等
    ↓
Phase2（Web版本）→ Spring Boot + Vue控制台
```

**V1不可取代的原因**：
1. 验证CLI + 流程调度核心功能
2. 验证TDD流程（先写测试再写代码）
3. 为V2提供稳定基础

---

## V1设计（最小版本）

**目标**：核心功能 + TDD验证

### V1模块清单

| 模块 | 职责 | 优先级 |
|------|------|--------|
| state_machine | 七状态模型 | P0 |
| task_manager | 任务CRUD | P0 |
| scheduler | 流程调度 | P0 |
| cli_interface | CLI命令 | P0 |
| checkpoint | 状态快照 | P1 |
| employee_pool | 三层员工池 | P2 |
| knowledge_retrieval | 三层检索 | P2 |

### V1范围

- ✅ CLI交互
- ✅ 任务创建/查询/更新
- ✅ 状态流转（七状态模型）
- ✅ 流程调度
- ✅ Checkpoint保存/恢复
- ❌ WebSocket通信（V2）
- ❌ Agent提炼（V2）
- ❌ 前置拆分（V2）
- ❌ Web控制台（Phase2）

### V1验收标准

- 271测试通过（单元+集成+E2E）
- TDD流程验证可行
- CLI可用

---

## V2设计（扩展版本）

**前提**：V1完成并通过验收

### V2追加内容

| 设计文档 | 问题 | 方案 |
|----------|------|------|
| 01_通信层设计 | HTTP延迟 | WebSocket+SSE |
| 02_Agent提炼机制 | 死循环刷屏 | 分层提炼 |
| 03_前置拆分流程 | 上下文膨胀 | Phase0拆分 |
| 04_强制checkpoint | 被动不可靠 | 阻塞式注入 |
| 05_子Agent异步总结 | 阻塞主任务 | Haiku异步 |
| 06_Claude_Code输出格式 | 提取困难 | 解析规范 |
| 08_V3_Checkpoint版本快照优化 | 无法回退代码 | Git绑定+文件边界 |

### V2新增模块

| 模块 | 职责 | 基于V1 |
|------|------|--------|
| websocket_client | WebSocket通信 | 新增 |
| session_parser | 解析.jsonl | 新增 |
| thinking_filter | 死循环检测 | 新增 |
| phase_reviewer | 阶段复盘 | 新增 |
| task_reviewer | 任务复盘 | 新增 |
| progress_reporter | 进度推送 | 新增 |
| alert_handler | 告警处理 | 新增 |
| checkpoint | LangGraph接口 | 修改V1 |

---

## Phase2设计（Web版本）

**前提**：V2完成

- Spring Boot后端
- Vue前端
- WebSocket + SSE通信
- Web控制台UI

---

## V2.2.0 Web控制台

| 模块 | 职责 | 文件 |
|------|------|------|
| TaskController | REST API | controller/TaskController.java |
| CheckpointController | Checkpoint API | controller/CheckpointController.java |
| SseController | SSE推送 | sse/SseController.java |
| PythonWebSocketHandler | WebSocket处理 | websocket/PythonWebSocketHandler.java |
| TaskService | 任务业务 | service/TaskService.java |
| CheckpointService | Checkpoint业务 | service/CheckpointService.java |
| CleanupScheduler | 定时清理 | scheduler/CleanupScheduler.java |
| Dashboard | 主页面 | views/Dashboard.vue |
| TaskDetail | 详情页 | views/TaskDetail.vue |
| StatsCard | 统计卡片 | components/StatsCard.vue |
| TaskCard | 任务卡片 | components/TaskCard.vue |
| WorkflowProgress | 工作流进度 | components/WorkflowProgress.vue |
| StepScroller | 步骤滚动 | components/StepScroller.vue |
| CheckpointTimeline | 时间线 | components/CheckpointTimeline.vue |
| TaskIdBox | 任务ID | components/TaskIdBox.vue |
| InterventionModal | 介入弹窗 | components/InterventionModal.vue |
| TaskStore | 状态管理 | stores/taskStore.ts |
| api.ts | API服务 | services/api.ts |
| sse.ts | SSE服务 | services/sse.ts |

---

---

## Agent Token治理架构

> 设计文档: [2026-04-21-agent-token-governance-design.md](superpowers/specs/2026-04-21-agent-token-governance-design.md)

五层治理体系：熔断层 + 快照层 + 验收层 + 工具层 + 恢复层

核心模块：
| 模块 | 职责 | 实现方式 |
|------|------|----------|
| 熔断机制 | 探索阶段硬阈值拦截 | 10轮上限 + 50K累计Token + 相似度检测(bge-small-zh) |
| 快照体系 | 基线+增量双轨快照 | JSON模板 + Git绑定 |
| 验收分层 | 三级自动化验收 | L1强制量化 + L2半量化 + L3纯人工 |
| 工具治理 | Hook文件读取限流 | PostToolUse拦截 + Prompt兜底 |
| 异常恢复 | 熔断后自动回滚 | 快照回滚 + 增量记录 |

---

## V2.3.0 异步复盘模块

| 模块 | 职责 | 文件 |
|------|------|------|
| HaikuClient | Haiku API调用 | claudeflow/haiku_client.py |
| PhaseReviewer | Phase级复盘 | claudeflow/phase_reviewer.py |
| TaskReviewer | Task级复盘+知识提取 | claudeflow/task_reviewer.py |

**测试覆盖**：
- 30个单元测试（Mock模式）
- WebSocket集成测试（Python→Java）
- SSE稳定性测试
- 总覆盖率 88%（310测试通过）

**待验证**（需Java 17+环境）：
- 真实后端集成测试
- Python→WebSocket实时通信
- 大量步骤滚动性能

---

## V2.4.0 CLI驱动模块

| 模块 | 职责 | 文件 |
|------|------|------|
| CliDriver | CLI进程驱动 | claudeflow/cli_driver.py |
| CliSession | 会话信息管理 | claudeflow/cli_driver.py |

**核心机制**（基于验证报告）：
- 启动：`claude -p "prompt" --output-format stream-json --verbose`
- session追踪：从首事件提取session_id
- 干预：`claude -p --resume session_id "新prompt"`
- 解析：assistant事件包含thinking/tool_use/text

**测试覆盖**：
- 40个单元测试（Mock模式）
- 覆盖率96%
- 会话生命周期测试
- 干预恢复测试

---

## V2.4.0 指令集注入整合

| 文件 | 职责 |
|------|------|
| CLAUDE.md | Hermes管理者指令段 |
| test_hermes_cli_integration.py | Hermes CLI集成测试 |

**注入内容**：
- 核心身份定义：ClaudeFlow是任务调度管理系统，不是直接执行者
- 启动命令模板：subprocess启动CLI
- 干预命令模板：--resume恢复会话
- 事件解析规则：tool_use→进度追踪，text→阶段完成，result→任务完成
- 干预时机：质量检查、人工介入、异常检测

**测试覆盖**：
- 19个集成测试
- Hermes启动CLI并捕获session_id
- Hermes监控事件流并报告进度
- Hermes创建checkpoint
- Hermes干预会话（质量检查）
- Hermes检测任务完成

**总测试覆盖**：
- 379个测试通过
- 总覆盖率88%

---

## Runtime实现记录

> 实现文档: [09_Runtime实现与变更记录.md](09_Runtime实现与变更记录.md)
>
> 月度路线图: [specs/2026-04-24-runtime-monthly-roadmap.md](specs/2026-04-24-runtime-monthly-roadmap.md)
>
> 清理分析: [specs/2026-04-24-hermes-legacy-cleanup-analysis.md](specs/2026-04-24-hermes-legacy-cleanup-analysis.md)
>
> 清理规格: [specs/2026-04-24-hermes-legacy-cleanup-spec.md](specs/2026-04-24-hermes-legacy-cleanup-spec.md)

当前仓库已经额外落地了一个面向多会话 runtime 的 PoC，和旧的 V1/V2 设计并行存在：

- Python 侧拆分出 `runtime/` 与 `workflow/`
- 支持 `runtime start / complete / fail / dispatch / plan / explain`
- Hermes 已暴露 `runtime status / sessions / plan / explain / dispatch`
- Vue console 已新增独立 `/runtime` 工作台
- 后续 runtime / console 相关改动必须同步更新实现文档
- 下一阶段优化需求已拆分为 4 份独立 spec，统一由月度路线图管理
- Hermes 遗留清理已补充专项分析和专项规格，供后续独立执行

---

## 下一步

1. **创建GitHub仓库**
2. **V1开发**（TDD流程）
3. **V1验收**
4. **V2扩展**（基于V1）
5. **Phase2开发**（Web版本）
