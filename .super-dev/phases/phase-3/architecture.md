# Phase 3 Architecture

## 总体方案

Phase 3 采用“协议先固定，消费面再收口”的增量方案：

```text
src/claudeflow/runtime/api.py
src/claudeflow/runtime/manager.py
src/claudeflow/governance/*
        ↓
examples/runtime-*.schema.json + examples/runtime-*.sample.json
        ↓
console/src/services/runtimeApi.ts + parse/validate layer
console/src/views/RuntimeConsole.vue + runtime components/composables
        ↓
src/main/java/com/claudeflow/controller/TaskController.java
src/main/java/com/claudeflow/service/TaskService.java
```

## 模块职责

### 1. Python runtime / governance

职责：

- 提供 runtime 与治理主真相源
- 输出稳定字段集合
- 不感知具体前端样式

主路径：

- `src/claudeflow/runtime/api.py`
- `src/claudeflow/runtime/manager.py`
- `src/claudeflow/governance/*`

### 2. Schema / Sample 层

职责：

- 固定 `status / sessions / plan / explain / dispatch / events` 协议
- 给前端、测试和外部消费面提供同一份约束基线

主路径：

- `examples/runtime-*.schema.json`
- `examples/runtime-*.sample.json`

### 3. Console 服务与校验层

职责：

- 从 runtime API 拉取数据
- 在进入 UI 前完成 parse / validate
- 将错误包装成可显示状态

建议结构：

```text
console/src/services/runtimeApi.ts
console/src/composables/useRuntimeLiveData.ts
console/src/composables/useRuntimeActions.ts
console/src/types/runtime.ts
console/src/validators/runtime.ts
```

### 4. Console 展示层

职责：

- 只负责页面编排、组件展示和用户交互
- 不直接堆叠 API 调用和状态拼装逻辑

主路径：

- `console/src/views/RuntimeConsole.vue`
- `console/src/components/runtime/**`

### 5. Java 控制面

职责：

- 明确旧任务流 REST 接口边界
- 为 console 或外部系统提供可解释的聚合入口
- 不复制 Python runtime 业务逻辑

主路径：

- `src/main/java/com/claudeflow/controller/TaskController.java`
- `src/main/java/com/claudeflow/service/TaskService.java`
- 必要时新增 `client/` 与 DTO 聚合层

## 数据流

### 1. Runtime 只读链

```text
runtime/api.py
→ runtimeApi.ts
→ validate/parse
→ RuntimeConsole composables
→ Runtime components
```

### 2. 高影响动作链

```text
Runtime Console action click
→ confirmation step
→ runtimeApi action request
→ action result / error
→ audit record write or fetch
→ UI feedback + recent action list
```

### 3. Java 外部消费链

```text
Java controller/service
→ consume runtime-facing contract
→ translate to console-facing DTO only when necessary
→ return stable HTTP response
```

## 架构约束

1. 不新增第二套 runtime 真相源
2. 不让 Java 服务层复制 Python runtime 状态机
3. 不在 `RuntimeConsole.vue` 内继续堆大段数据获取与动作实现
4. 协议字段只能先改 schema/sample，再改消费层
5. 任何 console 交互改动都必须同步更新 `docs/runtime/changelog.md`

## 阶段验收焦点

1. Console 是否从“单文件堆逻辑”变成“协议校验 + composable + 组件编排”
2. 高影响动作是否具备确认和审计
3. Java/HTTP 消费面是否不再与 runtime 主链脱节
