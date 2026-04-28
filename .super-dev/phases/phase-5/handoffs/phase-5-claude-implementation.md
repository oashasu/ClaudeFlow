# Phase 5 Claude 实现交接

## 角色边界

- `Claude` 负责实现 `T501 ~ T506`
- `Codex` 继续担任 Governor，只做任务分发、审查、返工裁决和 gate 决策
- 本阶段不允许由 Codex 直接承担主实现任务

## 输入文档

- `../research.md`
- `../prd.md`
- `../architecture.md`
- `../uiux.md`
- `../acceptance.md`
- `../spec.md`
- `../task-plan.md`
- `../tasks/T501.yaml`
- `../tasks/T502.yaml`
- `../tasks/T503.yaml`
- `../tasks/T504.yaml`
- `../tasks/T505.yaml`
- `../tasks/T506.yaml`

## 实现总目标

把 Phase 1-4 已经收口的 Runtime 主线整理成一套可交付、可发布、可回滚的工程化基线：

```text
python / console / java / smoke evidence
→ release checklist
→ release gate execution path
→ readiness / warning budget classification
→ post-release verification
→ rollback + delivery summary
```

## 执行顺序

1. 先做 `T501`，固化 release checklist 与 quality gate 矩阵
2. 再做 `T502`，建立统一发布门禁入口或命令组
3. `T503` 收口 release readiness / warning budget / blocker 分层
4. `T504` 补发布后验证说明
5. `T505` 固化回滚约定与交付摘要模板
6. `T506` 做阶段回归与 release-ready 决策证据

## 必须满足

1. 不得把单侧测试通过误写成整体 release-ready
2. 不得用抽象文档代替仓库内真实可运行命令
3. blocker、non-blocker、warning budget 必须清晰分层
4. 发布后验证必须覆盖 runtime 关键主链
5. 回滚说明必须包含触发条件与复验命令
6. 文档、脚本、状态门禁三者必须同步
7. 不得回退 Phase 1-4 已验收能力

## UI 冻结约束

- 图标库: `lucide-vue-next`
- 字体: `IBM Plex Sans` + `JetBrains Mono`
- 颜色和视觉语言必须服从 `../uiux.md`
- 禁止 emoji 图标
- 禁止新增第二套 release 工具台或聊天式壳层

## 本阶段不做

1. 新 Runtime Console 功能
2. 新 runtime API 业务扩展
3. 前端测试 harness 二次重构
4. 大规模 CI/CD 平台迁移
5. 生产自动部署系统重写

## 回传要求

- `changed_files`
- `summary`
- `test_evidence`
- `known_issues`
- 如有未完成项，必须逐条列出
