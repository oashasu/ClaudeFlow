# Phase 5 UIUX

## 结论

Phase 5 不是新的产品界面阶段，UI/UX 重点是“交付信息呈现方式”，不是 Runtime Console 视觉改版。

## 延续的 UI 工具链

### 图标库

- 继续使用 `lucide-vue-next`

禁止：

- emoji
- 混入未冻结的临时图标集

### 字体系统

- 继续使用 `IBM Plex Sans`
- 等宽字体继续使用 `JetBrains Mono`

### 设计 token system

沿用 Phase 3/4 已冻结 token，不切换主题方向。Phase 5 若需要新增发布态提示，只能在现有 token 语义内扩展：

- `accent-success` 用于 release-ready
- `accent-warning` 用于 non-blocker warning
- `accent-danger` 用于 release blocker
- `accent-info` 用于 verification / smoke 状态

## 页面骨架约束

Phase 5 不新增第二套控制台。若出现交付信息展示，只允许以下两类落点：

1. 文档化展示
2. 现有 Runtime Console / Dashboard 内的低扰动状态提示

禁止：

1. 为 release engineering 单独起一套新前端工作台
2. 把 Governor 审核信息做成聊天式侧栏壳
3. 把测试日志原样堆进主操作区

## 交互规则

1. 发布状态应以清晰层级区分 `ready / warning / blocked`
2. warning 说明要可点击追溯到具体命令或文档，而不是一句抽象提示
3. 回滚说明属于运维辅助层，不应挤占 Runtime 主操作区
4. 若新增 release summary 视图，必须以摘要卡片 + 证据链接为主，不展示海量原始日志

## 验收视觉标准

1. 交付信息呈现与 Phase 3/4 的视觉语言保持一致
2. 发布 blocker 与环境噪音有明确视觉分级
3. 不新增风格漂移，不回退到 debug 面板式 UI
4. 所有交付状态提示都应服务决策，不应喧宾夺主
