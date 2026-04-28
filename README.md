# ClaudeFlow

> AI 驱动的任务编排与执行系统

## 项目概述

ClaudeFlow 是一个基于 Claude Code 的任务管理系统，实现：
- CLI 交互式任务管理
- 七状态模型任务流转
- 流程调度与 checkpoint 机制
- 三层员工池与知识检索

## 分支规范

使用语义化版本号作为分支名：

| 版本类型 | 分支名 | 迭代力度 |
|----------|--------|----------|
| 主版本 | `v1.0.0` | 重大里程碑 |
| 次版本 | `v1.1.0` | 新功能/模块 |
| 补丁版本 | `v1.0.1` | Bug 修复/小改动 |

AI 助手可根据迭代力度自主决定是否创建新分支。

## 分阶段开发策略

```
V1（最小版本）→ 验证核心功能 + TDD流程可行性
    ↓
V2（扩展版本）→ 在V1基础上添加通信层/提炼机制等
    ↓
V2.1.0（Checkpoint增强）→ 强制checkpoint + 异步总结
    ↓
V2.2.0（Web控制台）→ Spring Boot后端 + Vue前端控制台
    ↓
V2.2.1（sessionId获取）→ 修复sessionId获取方式
    ↓
V2.3.0（异步复盘）→ haiku_client/phase_reviewer/task_reviewer + 集成测试
    ↓
Phase2（完整Web版本）→ 功能扩展与优化
```

## 目录结构

```
claudeflow/
├── docs/           # 设计文档
├── src/            # Python源代码
│   └── main/java/  # Spring Boot后端
├── tests/          # 测试代码
├── console/        # Vue前端控制台
└── README.md       # 项目说明
```

## 仓库地址

- GitHub: https://github.com/oashasu/ClaudeFlow

## 快速开始

```bash
# 克隆仓库
git clone git@github.com:oashasu/ClaudeFlow.git

# 切换到V1分支
git checkout v1.0.0
```

## Runtime PoC

当前版本已包含最小多会话 runtime PoC，可通过 CLI 初始化运行时目录并启动/完成 worker：

```bash
claudeflow runtime init

claudeflow runtime status

claudeflow runtime show --task-id impl_auth_controller

claudeflow runtime start \
  --task-id impl_auth_controller \
  --prompt "实现 AuthController" \
  --write-path src/controllers/AuthController.java \
  --protocol-ref auth_api@v2

claudeflow runtime start \
  --task-id impl_auth_controller \
  --task-graph-file ./examples/task-graph.json

claudeflow runtime dispatch \
  --task-graph-file ./examples/task-graph.sample.json \
  --max-concurrent 2

claudeflow runtime explain \
  --task-id impl_auth_tests \
  --task-graph-file ./examples/task-graph.sample.json

claudeflow runtime plan \
  --task-graph-file ./examples/task-graph.sample.json

claudeflow runtime plan \
  --task-graph-file ./examples/task-graph.sample.json \
  --json

claudeflow runtime explain \
  --task-id impl_auth_tests \
  --task-graph-file ./examples/task-graph.sample.json \
  --json

claudeflow runtime dispatch \
  --task-graph-file ./examples/task-graph.sample.json \
  --json

claudeflow runtime complete \
  --task-id impl_auth_controller \
  --summary "Controller 已实现" \
  --changed-file src/controllers/AuthController.java \
  --test-status passed \
  --test-count 3

claudeflow runtime fail \
  --task-id impl_auth_controller \
  --reason "测试失败，需要人工介入"
```

`runtime complete` 现在会直接输出新变为 runnable 的任务，便于继续调度下一批节点；`runtime fail` 会把任务标记为失败，并让 runtime 状态进入 `intervention_required = true`。
`runtime dispatch` 会按任务 `priority` 排序启动可运行节点，并输出当前 blocked 任务及其原因，例如“等待依赖完成”或“上游失败，按策略跳过”；`--max-concurrent` 会按当前 active session 数量计算剩余槽位。`runtime explain` 可单独解释某个任务现在为什么不能跑，`runtime plan` 则会汇总 runnable / blocked / running 三类任务。blocked 和 skipped 结果现在同时带 `reason_code`，且 `dispatch / plan / explain` 都支持 `--json`，便于后续控制台或自动化逻辑稳定消费。

## Runtime Console

当前仓库已经新增独立的 runtime 工作台页面 `/runtime`，它和旧的 `Dashboard / TaskDetail` 分层存在：

- 旧页面负责任务流视图
- `Runtime Console` 负责 runtime / session / dispatch 视图

当前 Runtime Console 已支持：

- sample / live 双模式
- live `status / sessions / plan / explain / dispatch`
- 自动刷新
- session 列表动作：
  - `解释任务`
  - `查看事件`
  - `发送干预`
  - `标记完成`
  - `标记失败`
- session inspector：查看当前 session 事件流与摘要
- 旧 `Dashboard / TaskDetail` 到 Runtime Console 的入口跳转

## 文档同步约束

从 2026-04-24 起，凡是涉及 runtime、Hermes runtime API、Runtime Console 的功能更新，都必须同步更新实现文档：

- [docs/runtime/changelog.md](docs/runtime/changelog.md)
- [docs/README.md](docs/README.md) — 文档导航入口

如果改动了输出结构或对象协议，还需要同步更新 `examples/*.schema.json`。

## 文档索引

详见 [docs/INDEX.md](docs/INDEX.md) 或 [docs/README.md](docs/README.md)
