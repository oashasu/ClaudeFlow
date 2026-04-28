# Phase 5 Acceptance

## 状态: 待实现

## A51 Release Checklist 固化

- 期望
  - 仓库内存在一份明确的发布前 checklist
  - checklist 至少覆盖 Python、Console、Java、smoke 和文档一致性检查

## A52 Quality Gate 统一入口

- 期望
  - 发布前门禁命令有统一入口或统一命令组
  - 门禁顺序明确，可复跑，可被 governor 直接引用

## A53 Release Readiness 分层

- 期望
  - blocker、non-blocker、warning budget 有清晰分层
  - 环境级 warning 与功能性回归不再混为一谈

## A54 发布后验证说明

- 期望
  - 文档明确说明发布后最小验证链
  - 至少覆盖 runtime status、sessions、events、dispatch|audit 等关键读链

## A55 回滚约定

- 期望
  - 文档明确说明何时触发回滚
  - 明确回滚后需要重验的命令和主链

## A56 Phase 5 回归与交付决策

- 期望
  - Phase 5 新增工程化产物不回退 Phase 1-4 已验收主链
  - governor 可基于 Phase 5 产物做出一致的 `release-ready / not-ready` 决策

## Blocker 条件

以下任一项即阻断：

1. release checklist 缺少 Python、Console、Java、smoke 任一关键门禁
2. 发布命令或脚本与仓库当前真实可运行方式不一致
3. blocker / warning budget 口径仍然混乱，无法支持发布决策
4. 发布后验证或回滚说明只有抽象描述，没有真实命令
5. 为完成 Phase 5 而回退 Phase 3/4 已验收主链
