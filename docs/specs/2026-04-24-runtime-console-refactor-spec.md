# Runtime Console 结构重构规格

> 状态：`pending`
>
> 优先级：`P1`

## 1. 目标

将 Runtime Console 从“单文件堆逻辑”重构为“状态驱动 + 组件组合”的结构。

## 2. 背景问题

当前 `RuntimeConsole.vue` 已同时承担：

- sample/live 数据源管理
- 轮询
- session events 拉取
- action 请求
- 成功/失败提示
- plan/explain/dispatch 状态拼装

继续在这个结构上堆功能，维护成本会快速上升。

## 3. 目标结构

建议至少拆成：

- `useRuntimeLiveData()`：拉取 `status / sessions / plan / explain / dispatch`
- `useRuntimeActions()`：处理 `intervene / complete / fail`
- 视图组件层：只负责展示和事件派发

## 4. 范围

涉及：

- `console/src/views/RuntimeConsole.vue`
- `console/src/components/runtime/**`
- 新增 `console/src/composables/**`

## 5. 非目标

- 不改 Dashboard 的数据模型
- 不改旧任务流 store
- 不在本阶段引入全局状态管理重写

## 6. 严格验收标准

1. `RuntimeConsole.vue` 中不再直接堆积主要数据获取和动作实现逻辑，主页面职责应收敛为“拼装组件 + 绑定 composable”。
2. 轮询逻辑和 session action 逻辑至少拆成 2 个独立模块。
3. 重构后现有功能不能倒退：
   - sample/live 切换
   - 自动刷新
   - explain
   - dispatch
   - 查看 session events
   - intervene / complete / fail
4. 新结构必须补充独立单测，至少覆盖：
   - 轮询状态变化
   - action 成功
   - action 失败
   - 页面装配
5. 重构后 Runtime Console 的交互文案和入口位置不能比当前更混乱。
