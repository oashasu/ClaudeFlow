# Hermes系统设计 - V2版本规划

> **日期**: 2026-04-19
> **状态**: V2设计阶段启动

---

## 版本演进

| 版本 | 状态 | 说明 |
|------|------|------|
| V1 |已完成 ✅ | Phase1核心模块 + 271测试 |
| V2 | 设计中 🔄 | 追加通信层 + Agent提炼 + 前置拆分 |

---

## V1成果（保留）

- 7个核心模块（state_machine, task_manager, employee_pool, knowledge_retrieval, checkpoint, cli_interface, scheduler）
- 271测试全部通过（单元219 + 集成42 + E2E10）
- API文档 + CLI手册 + 验收报告

---

## V2追加设计内容

### 1. Phase2通信层设计

**问题**: HTTP REST在人工介入场景实时性不足

**方案**:
- Python → Java: WebSocket（双向实时）
- Java → Vue: SSE（单向推送）
- Vue → Java: HTTP POST（用户操作）

**关键场景**: 人工介入需要实时双向通信

### 2. Agent提炼机制设计

**问题**: Claude Code会话可能死循环刷屏，原始日志暴涨

**方案**:
- 实时进度：从工具调用直接提取（无Agent）
- 阶段总结：主任务自己输出（进入下一阶段上下文）
- 阶段复盘：Haiku Agent异步（基于提炼日志）
- 任务复盘：Haiku Agent（汇总所有阶段）

**拒绝方案**: 记录原始会话内容（死循环问题）

### 3. 前置拆分流程设计

**问题**: 长任务上下文膨胀，执行质量下降

**方案**:
- Phase 0（前置拆分）：拆分Agent → 审查Agent → 确认 → 执行计划
- Phase 1-8（按计划执行）：子任务依次执行，强制checkpoint，上下文可控

**关键**: 拆分在前置阶段完成，执行阶段按计划执行，不做动态决策

### 4. 强制checkpoint机制

**问题**: 被动触发总结不可靠，system消息可能被忽略

**方案**:
- 子任务完成 → 强制注入prompt → 总结 → checkpoint → 继续
- 不是"提醒总结"，而是"必须总结才能继续"

### 5. 子Agent异步总结

**问题**: 总结阻塞主任务执行

**方案**:
- 子Agent（Haiku）异步执行总结
- 完成后系统级通知（不进对话历史，0膨胀）
- 主任务按需读取checkpoint

### 6. Claude Code输出格式规范

**问题**: 需要从Claude Code会话中提取工具调用和进度信息

**方案**:
- .jsonl文件格式解析规范
- 工具调用提取规则
- Thinking内容过滤规则（死循环检测）
- 会话内容提炼流程

---

## V2目录结构

```
/Users/claw/sandbox/tasks/2026-04-18_Hermes系统设计/
├── （V1内容保留）
├── V2_追加设计/
│   ├── 01_通信层设计.md
│   ├── 02_Agent提炼机制设计.md
│   ├── 03_前置拆分流程设计.md
│   ├── 04_强制checkpoint机制设计.md
│   ├── 05_子Agent异步总结设计.md
│   ├── 06_Claude_Code输出格式规范.md
│   ├── INDEX.md
│   └── checkpoint/
│       └── v14_v2_design_start.json
```

---

## V2设计文档清单（更新后）

| 文档 | 问题 | 方案 | 补充内容 |
|------|------|------|----------|
| 01_通信层 | HTTP延迟 | WebSocket+SSE | 断线重连、消息ACK、多Worker |
| 02_提炼机制 | 死循环刷屏 | 分层提炼 | .jsonl解析、存储路径、死循环检测 |
| 03_前置拆分 | 上下文膨胀 | Phase0拆分 | 拓扑排序、复杂度量化、拒绝处理 |
| 04_强制checkpoint | 被动不可靠 | 阻塞式注入 | 显式标记、版本兼容、命名规范 |
| 05_异步总结 | 阻塞主任务 | Haiku异步 | 触发读取、知识库索引 |
| 06_输出格式 | 提取困难 | 解析规范 | .jsonl格式、工具提取、过滤规则 |

---

## V2代码迭代计划（P1精简后）

```
Phase1 V1代码（保留）
    ↓
V2设计文档完成 + P1模块边界确定
    ↓
迭代Phase1代码（V2版本）
    ├── 新增：websocket_client.py（通信层）
    ├── 新增：session_parser.py（解析.jsonl + 工具摘要）
    ├── 新增：thinking_filter.py（过滤thinking + 死循环检测）
    ├── 新增：phase_reviewer.py（阶段复盘Haiku）
    ├── 新增：task_reviewer.py（任务复盘Haiku）
    ├── 新增：progress_reporter.py（进度推送WebSocket）
    ├── 新增：alert_handler.py（告警处理）
    ├── 修改：checkpoint.py（借鉴LangGraph接口）
    ├── 修改：scheduler.py（Session生命周期管理）
    ↓
Phase2开发（Spring Boot + Vue）
    ├── 基于V2设计直接实现
    ├── WebSocket + SSE通信层
    ├── Web控制台UI
```

---

## V2模块清单（精简后7模块）

| 层 | 模块 | 职责 | 状态 |
|----|------|------|------|
| 数据层 | CheckpointManager | 存取checkpoint | V1已有，V2增强 |
| 数据层 | KnowledgeStore | 存取知识库 | V1已有 |
| 处理层 | SessionParser | 解析.jsonl + 工具摘要 | V2新增 |
| 处理层 | ThinkingFilter | 过滤thinking + 死循环检测 | V2新增 |
| 处理层 | PhaseReviewer | 阶段复盘（Haiku） | V2新增 |
| 处理层 | TaskReviewer | 任务复盘（Haiku） | V2新增 |
| 协调层 | ProgressReporter | 进度推送WebSocket | V2新增 |
| 协调层 | AlertHandler | 告警处理 | V2新增 |

**已删除模块**：
- ~~ContextManager~~ → Session生命周期由Hermes直接管理
- ~~NodeSummarizer~~ → 合并到PhaseReviewer
- ~~DeadLoopDetector~~ → 合并到ThinkingFilter

---

## P1模块边界决策（已确定）

| 原重叠问题 | 解决方案 |
|------------|----------|
| SessionSummarizer vs CheckpointManager | 拆分职责 |
| PhaseReviewer vs NodeSummarizer | 合并为PhaseReviewer |
| ToolSummary vs SessionParser | ToolSummary是SessionParser子功能 |
| ContextManager vs CheckpointManager | **删除ContextManager**（开新Session即可） |
| DeadLoopDetector vs ThinkingFilter | 合并到ThinkingFilter |

**核心决策**："清空上下文"本质上就是开新Session，ContextManager无存在必要

---

## P8/P9调研结论（已确定）

### P8 Hermes必要性
**结论：必须存在**
- Claude无跨实例协调能力
- Claude无WebSocket/UI能力
- Claude无状态持久化API

### P9 开源方案借鉴
**结论：借鉴设计，不引入框架**

| 借鉴内容 | 来源 |
|----------|------|
| Checkpoint接口 | LangGraph `get_tuple/put/put_writes` |
| Task依赖声明 | CrewAI Task.context |
| 角色订阅机制 | MetaGPT _watch |

### SQLite-vec决策
**结论：暂不需要向量存储**
- deer-flow（62K stars）也未使用向量存储
- Hermes checkpoint用键值存储足够
- Hermes知识库用关键词检索足够

---

## 下一步

1. 创建V2_追加设计目录
2. 编写各设计文档
3. 创建v14 checkpoint
4. 更新memory记录