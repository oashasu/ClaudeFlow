# Phase 1 Architecture

## 目标结构

```text
.super-dev/phases/phase-1/tasks/*.yaml
        ↓
Governance Runtime Adapter
        ↓
RuntimeTaskSpec
        ↓
RuntimeManager
        ↓
DriverRegistry
  ├── ClaudeDriver
  └── CodexDriver
        ↓
Session Index / Result Collector
```

## 模块划分

### 1. Governance Runtime Adapter

职责：

- 读取 `TaskPackage`
- 生成 runtime 可执行对象
- 映射 `executor_type / allowed_write_paths / acceptance_refs / constraints`

### 2. RuntimeDriver

职责：

- 统一不同宿主的启动、监控、干预、取消、结果回收接口

### 3. ClaudeDriver

职责：

- 封装现有 `CliDriver`
- 保持现有 Claude 路径兼容

### 4. CodexDriver

职责：

- 提供 `codex` 宿主的最小执行/可测试入口
- 将宿主细节限制在 driver 内部

### 5. DriverRegistry

职责：

- 根据 `executor_type` 返回 driver
- 对不支持值给出结构化错误

### 6. RuntimeManager 改造点

- 调度对象新增 `executor_type`
- 不再用 `owner_role` 选择宿主
- session index 增加 `executor_type / driver_name / known_issues / test_evidence`

## 架构约束

1. Phase 1 只改 Python runtime 主链。
2. 不改 Java / Spring 旧调度链。
3. 不在 RuntimeManager 内部硬编码宿主分支替代 registry。
4. 不允许继续依赖手工维护平行 task graph。
