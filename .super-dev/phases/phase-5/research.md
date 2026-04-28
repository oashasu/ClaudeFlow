# Phase 5 Research

## 阶段名称

- `phase-5`
- `交付与发布工程化`

## Phase 4 之后的真实缺口

Phase 4 已经把 Runtime Console 的测试噪音、错误路径和 smoke 入口收口为可维护基线，但当前仓库仍缺少“面向交付”的最后一层工程化能力：

1. 已有测试与 smoke 证据分散在手工命令和 review artifact 中，还没有统一 release checklist
2. Phase 3/4 虽然能本地复跑，但缺少明确的质量门禁编排顺序，容易出现“只跑一部分就当可发布”
3. Python / Console / Java 三侧的构建与验证口径还没有统一成一套发布前验收流程
4. 当前 review 会记录非阻断 warning，但没有明确的 release 口径去区分“允许发布的环境噪音”和“必须阻断的回归”
5. 缺少部署前后检查、回滚前提、交付证据归档方式，导致后续 phase 还要重复解释“什么叫可发版”

这些问题不再是 Runtime 功能实现问题，而是发布治理和交付工程问题。

## 本阶段目标

Phase 5 的目标是把已经存在的实现、测试和 smoke 主链整理成一套可执行的交付门禁：

```text
unit/integration/smoke evidence
→ release checklist
→ quality gate command set
→ delivery artifact summary
→ rollback / verification contract
→ release-ready baseline
```

## 本阶段优先级判断

### P0

1. 固化发布前质量门禁命令与执行顺序
2. 建立 release checklist 与交付摘要模板
3. 明确 blocker / non-blocker / warning budget 的发布口径
4. 补齐最小部署验证与回滚说明

### P1

1. 统一 Python / Console / Java 的发布证据格式
2. 为后续 phase 提供可复用的 release readiness 文档与脚本入口
3. 收口 Phase 3/4 governor review 中留下的环境级 warning 说明

## 本阶段范围

### In Scope

1. 发布前 checklist、quality gate、delivery summary 文档
2. 构建 / 测试 / smoke 的统一执行入口或统一命令约定
3. release readiness 判定标准
4. 最小回滚与发布后验证说明
5. 对现有 warning 的发布级别分类

### Out of Scope

1. Runtime Console 新功能
2. 新 runtime API 业务能力
3. 新一轮前端测试 harness 改造
4. 大规模 CI 平台迁移
5. 生产部署自动化重构

## 关键设计判断

1. Phase 5 应该以“发布可判断、交付可复现”为核心，而不是继续扩功能
2. 工程化输出优先采用仓库内真实可复跑命令，不引入脱离现状的理想化流程
3. release checklist 必须覆盖 Python、Console、Java 和 smoke 证据，而不是只看单侧绿灯
4. warning 不应一刀切；需要区分会阻断发布的功能噪音与可接受的环境级噪音
5. 文档、脚本、状态门禁三者必须一致，避免再次出现“review 说能发，索引却写不清”的情况

## 阶段完成定义

只有同时满足以下条件，Phase 5 才算完成：

1. 存在一套明确的 release checklist 和 quality gate 顺序
2. 交付前至少有一条统一入口或统一命令组可复跑 Python / Console / Java / smoke
3. blocker / non-blocker / warning budget 有明确发布口径
4. 部署后验证与回滚前提被写成仓库内真实文档
5. governor 可以基于这些产物做出“release-ready / not-ready”的一致判断
