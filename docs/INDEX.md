# ClaudeFlow系统设计

> **日期**: 2026-04-19
> **项目位置**: `/Users/claw/sandbox/personal/claudflow/`

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

## 设计问题清单

见 [07_V2设计问题清单.md](07_V2设计问题清单.md)

已解决：P1模块边界、P8必要性、P9开源方案
待解决：P2-P7（可在开发阶段逐步解决）

---

## 下一步

1. **创建GitHub仓库**
2. **V1开发**（TDD流程）
3. **V1验收**
4. **V2扩展**（基于V1）
5. **Phase2开发**（Web版本）