# Phase 1 Research

## 阶段定位

Phase 1 对应 ClaudeFlow 增强路线图中的 `Phase B：多宿主执行层`。

本阶段目标不是继续补治理模型，而是把 Phase A 已经落地的治理真相源真正接入 runtime 执行主链，让 `executor_type` 从文档字段变成可调度能力。

## 已确认输入

本阶段设计冻结依据：

- `task_archive/.../06_SuperDev多模型统一编排增强设计.md`
- `task_archive/.../07_Governor与ClaudeFlow协同协议.md`
- `task_archive/.../08_CodexGovernor宿主落地设计.md`
- `task_archive/.../09_Governor编排对象Schema设计.md`
- `task_archive/.../PhaseB_多宿主执行层文档包/`

## 当前代码现状

Python 侧已有：

- `claudeflow.runtime.manager.RuntimeManager`
- `claudeflow.runtime.cli_driver.CliDriver`
- `claudeflow.runtime.api`
- `claudeflow.cli` 的 runtime 子命令
- Phase A 已完成的 `governance` 模块

当前缺口：

- runtime 仍是单宿主 Claude 路径
- `executor_type` 还未进入 runtime 主调度链
- 治理任务包还未直接转为 runtime 调度对象
- session index 未完整记录宿主信息

## 本阶段边界

### 必须做

- RuntimeDriver 抽象
- ClaudeDriver / CodexDriver
- governance task → runtime task 适配
- 宿主感知 dispatch
- 宿主感知 session index / result collection
- CLI/API 最小增强

### 明确不做

- review artifact 自动生成
- rework 自动生成
- advance / reopen 自动裁决
- Java / Spring 调度链改造
- UI / Console 增强
