# Phase 4 Acceptance

## 状态: 待实现

## A41 前端 warning 收口

- 期望
  - Runtime Console 相关前端测试默认运行时不再打印已知 lifecycle warning
  - `action-audit` 的 fetch warning 不再作为默认测试噪音出现

## A42 测试 harness 标准化

- 期望
  - `useRuntimeLiveData`、`useRuntimeActions` 等 composable 测试运行在标准 Vue setup/harness 中
  - runtime API mock、flush、mount 方式有统一基座，不再在 spec 中散落重复封装

## A43 Audit / Live Data 错误路径稳定

- 期望
  - action audit 的成功、空数据、失败路径都有稳定断言
  - live payload parse/validate 失败路径可断言、可回归、可预测

## A44 Runtime Smoke 可复跑

- 期望
  - 仓库内存在一条真实可运行的 runtime smoke 入口
  - smoke 至少覆盖 `status / sessions / events / explain|dispatch / action result|audit` 的最小主链

## A45 文档与观测说明同步

- 期望
  - 文档明确说明测试入口、mock 约定、smoke 入口和排障顺序
  - Phase 3 审核里积累的 warning / 失败口径已被整理为可维护说明

## A46 Phase 4 回归

- 期望
  - Phase 4 新增收口不回退 Phase 3 的 Runtime Console 主功能
  - 回归结果可证明“测试干净度提升”不是通过删除失败路径实现

## Blocker 条件

以下任一项即阻断：

1. 前端测试仍默认打印已知 lifecycle warning 或 audit fetch warning
2. composable 测试仍通过裸调用绕过 Vue setup 生命周期
3. 为消除噪音而删除真实错误路径断言
4. smoke 只有文档描述，没有实际可运行入口
5. 为完成 Phase 4 而回退 Phase 3 已验收主链
