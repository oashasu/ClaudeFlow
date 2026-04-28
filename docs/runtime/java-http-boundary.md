# Java HTTP 控制层边界说明

> A35: 定义 Java 控制层与 Python Runtime 的消费契约边界

## 1. 边界划分

### TaskController (/api/tasks)
**职责**: 旧任务流 CRUD 操作

- 操作 TaskEntity（数据库持久化）
- 状态: pending, running, paused, waiting, completed, error, cancelled
- 真相源: MySQL 数据库
- 用途: 任务管理、状态查询、手动干预

### RuntimeController (/api/runtime-consume)
**职责**: Runtime API 消费代理

- 代理 Python Runtime API 调用
- 不持久化状态，只做 DTO 转换
- 真相源: Python Runtime Manager
- 用途: 实时 runtime 状态、plan/dispatch 信息、审计记录查询

### HermesClient vs RuntimeClient

| 客户端 | 调用目标 | 端点 | 用途 |
|--------|----------|------|------|
| HermesClient | Session 级 API | `/api/session/*` | 单会话生命周期管理 |
| RuntimeClient | Runtime 级 API | `/api/runtime/*` | 多任务调度与状态总览 |

## 2. 契约对齐

RuntimeClient 的 DTO 字段与 `examples/runtime-*.schema.json` 对齐：

- **RuntimeStatusResponse**: repo_path, active_agents, queued_tasks, completed_tasks, failed_tasks, intervention_required, running_tasks
- **RuntimeSessionDTO**: task_id, session_id, status, priority
- **RuntimePlanResponse**: runnable, blocked, running
- **RunnableTaskDTO**: task_id, priority, executor_type, phase_id
- **RuntimeExplainResponse**: task_id, state, priority, reason_code, reason, dependencies
- **RuntimeAuditRecordDTO**: action_id, action_type, target_task_id, target_session_id, success, message, timestamp

## 3. 禁止事项

1. **不得在 Java 层发明新字段约定** - 所有字段必须与 Python runtime schema 一致
2. **不得复制 Python runtime 状态机** - Java 只做代理和 DTO 转换，不重写调度逻辑
3. **不得持久化 Runtime 状态** - Runtime 状态真相源在 Python，Java 只读不写

## 4. 调用链

```
Java RuntimeController
  → RuntimeClient
  → HTTP 调用 Python Runtime API
  → DTO 转换（字段对齐）
  → 返回给 HTTP 客户端
```

## 5. 端点映射

| Java 端点 | Python 端点 |
|-----------|-------------|
| GET /api/runtime-consume/status | GET /api/runtime/status |
| GET /api/runtime-consume/sessions | GET /api/runtime/sessions |
| GET /api/runtime-consume/plan | GET /api/runtime/plan |
| GET /api/runtime-consume/explain/{taskId} | GET /api/runtime/explain/{task_id} |
| GET /api/runtime-consume/audit | GET /api/runtime/action-audit |

---
Generated: 2026-04-27T14:05:00Z