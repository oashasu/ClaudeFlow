# Phase 3 Task Plan

## 状态: 待分发

## 执行顺序

1. `T301` Runtime Console 结构重构
2. `T302` 高影响动作确认与审计链
3. `T303` runtime schema / sample / parse 校验
4. `T304` Java/HTTP 外部消费面契约收口
5. `T305` 文档、sample 与运行说明同步
6. `T306` Phase 3 回归与阶段验收测试

## 依赖关系

- `T302` 依赖 `T301`
- `T303` 依赖 `T301`
- `T304` 依赖 `T303`
- `T305` 依赖 `T301 + T302 + T303 + T304`
- `T306` 依赖 `T301 ~ T305`

## 宿主分配策略

- `Claude` 负责 Phase 3 实现任务
- `Codex` 继续负责 Governor 审查与 gate 决策
- 本阶段继续保持前端优先，再推进 Java/HTTP 消费面

## 每个任务的定义

### T301

- 目标: Runtime Console 结构收口，拆分 composable / validator / assembly
- 输出: 页面结构重构与状态获取主链
- 验收: `A31`

### T302

- 目标: 建立 `intervene / complete / fail` 确认与审计可见性
- 输出: action confirmation + audit feedback
- 验收: `A32`, `A33`

### T303

- 目标: 固化 runtime schema/sample 并接入前端 parse / validate
- 输出: 协议约束与错误可见性
- 验收: `A34`

### T304

- 目标: 收口 Java/HTTP 外部消费面与 runtime 契约
- 输出: controller/service 边界清理
- 验收: `A35`

### T305

- 目标: 同步实现文档、sample、操作说明
- 输出: 文档与样例一致性
- 验收: `A36`

### T306

- 目标: 补齐 Phase 3 回归与阶段验收测试
- 输出: 测试证据
- 验收: `A31`, `A32`, `A33`, `A34`, `A35`, `A36`

## 不属于本阶段

1. 权限系统 / RBAC
2. 宿主预算 / quota
3. 新增第二套前端
4. 新一轮治理状态机重写
