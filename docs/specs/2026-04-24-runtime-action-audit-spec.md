# Runtime 动作确认与审计规格

> 状态：`pending`
>
> 优先级：`P0`

## 1. 目标

为 Runtime Console 中的高影响动作建立受控执行链：

- `intervene`
- `complete`
- `fail`

## 2. 背景问题

当前这些动作已经可执行，但缺少：

- 二次确认
- 审计日志
- 最近一次操作结果查看
- 失败后的回放信息

这会直接影响调试和责任追踪。

## 3. 范围

涉及：

- `console/src/views/RuntimeConsole.vue`
- `console/src/components/runtime/**`
- `console/src/services/runtimeApi.ts`
- `src/claudeflow/hermes_service.py`
- `src/claudeflow/runtime/**`

## 4. 功能要求

### 4.1 确认机制

对 `complete` 和 `fail` 必须增加确认步骤。  
对 `intervene` 至少要在提交前显示目标 `task_id / session_id / prompt 摘要`。

### 4.2 审计日志

每次动作至少记录：

- action_id
- action_type
- task_id
- session_id
- requested_at
- input_summary
- result_status
- result_message

### 4.3 结果可见性

Runtime Console 必须能够看到：

- 最近一次动作结果
- 最近若干条动作记录
- 失败动作的错误信息

## 5. 非目标

- 不做完整 RBAC
- 不做跨用户权限系统
- 不做复杂审批流

## 6. 严格验收标准

1. 前端直接触发 `complete` 或 `fail` 时，没有确认不能真正发请求。
2. 每次 `intervene / complete / fail` 请求成功或失败后，都必须形成一条可查询的 action log。
3. action log 至少保留最近 20 条记录，且字段完整，不允许缺少 `action_type / task_id / result_status / requested_at`。
4. Runtime Console 中必须能看到最近一次动作结果；如果失败，必须能看到错误信息。
5. 至少补充：
   - 前端动作流测试
   - 后端动作日志测试
   - 失败分支测试
