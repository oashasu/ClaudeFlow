# Phase 5 PRD

## 阶段定位

Phase 5 负责把 Phase 1-4 已交付的 Runtime 主线整理为可发布、可复核、可回滚的工程化基线。

## 用户故事

### US-1 Governor / 发布决策者

作为 Governor，我需要一套明确的 release readiness 标准，这样在 review 通过后可以直接判断“能不能发”，而不是再人工拼接各类测试证据。

### US-2 交付执行者

作为交付执行者，我需要一份统一的 checklist 和命令顺序，这样在发版前不会遗漏 Console、Python、Java 或 smoke 任何一个关键门禁。

### US-3 维护者

作为维护者，我需要知道哪些 warning 属于环境噪音、哪些属于发布 blocker，避免把同一类问题在每次 phase 重复争论。

### US-4 回归审查者

作为审查者，我需要发布后验证和回滚前提都写在仓库里，这样一旦回归失败，可以快速定位是构建、协议、运行态还是发布流程问题。

## 范围

### In Scope

1. release checklist
2. quality gate 与 release readiness 标准
3. 统一测试/构建/smoke 命令口径
4. delivery evidence 与发布摘要模板
5. 发布后验证与回滚说明

### Out of Scope

1. 新产品能力开发
2. 新测试框架迁移
3. 全量 CI/CD 平台改造
4. 生产环境自动部署脚本重写
5. 新监控平台接入

## 功能要求

1. 仓库内必须存在一份发布前 checklist，至少覆盖：
   - Python 测试
   - Console 测试
   - Java 测试
   - runtime smoke
   - 关键文档同步检查
2. 必须定义 release-ready 的 blocker 条件，包括：
   - 功能性测试失败
   - smoke 失败
   - Phase 已验收主链回退
   - 文档/状态/证据口径不一致
3. 必须定义 non-blocker warning 口径，包括环境级 warning 的接受边界
4. 必须提供最小发布后验证说明，包括：
   - 如何验证 runtime status
   - 如何验证 sessions / events / dispatch / audit 主链仍可读
5. 必须提供最小回滚说明，包括：
   - 哪些前提触发回滚
   - 回滚后重新验证哪些门禁

## 质量围栏

1. 不允许只写概念性文档，不给真实命令
2. 不允许把“某一侧测试通过”误写成整体 release-ready
3. 不允许把 blocker 与环境噪音混成同一等级
4. 不允许新增发布流程文档却不同步 `.super-dev` 治理状态或 changelog
