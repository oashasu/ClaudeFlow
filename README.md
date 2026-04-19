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
Phase2（Web版本）→ Spring Boot + Vue控制台
```

## 目录结构

```
claudflow/
├── docs/           # 设计文档
├── src/            # 源代码
├── tests/          # 测试代码
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

## 文档索引

详见 [docs/INDEX.md](docs/INDEX.md)