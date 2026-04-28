# Phase 4 UIUX

## 结论

Phase 4 不是新 UI 功能阶段，但仍需要冻结 Runtime Console 的可观测性呈现规则，避免为了测试收口而把已有界面变回调试半成品。

## 延续的 UI 工具链

### 图标库

- 继续使用 `lucide-vue-next`

禁止：

- emoji
- 新增与现有风格不一致的临时图标

### 字体系统

- 继续使用 `IBM Plex Sans`
- 等宽字体继续使用 `JetBrains Mono`

### 设计 token system

沿用 Phase 3 已冻结的 token，不在本阶段切换主题方向：

```css
:root {
  --bg-canvas: #f4f1ea;
  --bg-panel: #fbf8f2;
  --bg-elevated: #fffdf8;
  --border-subtle: #d8d0c2;
  --text-strong: #1f1d1a;
  --text-muted: #5e574d;
  --accent-primary: #1f6b5b;
  --accent-primary-strong: #144d41;
  --accent-warning: #b7791f;
  --accent-danger: #a63f2f;
  --accent-info: #245c8a;
}
```

## 页面骨架约束

Runtime Console 仍保持 Phase 3 的五段式骨架，不新增第二工作台：

1. 顶部控制条
2. 运行态总览
3. 调度与解释区
4. session 主表
5. inspector / audit 区

本阶段允许的 UI 变更仅限：

1. 结构化错误卡片的可读性增强
2. audit 加载失败与空状态的统一呈现
3. smoke / connectivity 状态提示的低扰动展示

## 交互规则

1. warning 清理不能通过隐藏真实错误卡片来实现
2. audit 加载失败必须保留用户可见反馈，但测试态应可控、可断言
3. 任何新增的 observability 提示都应是辅助层，不得抢占主操作区
4. 不允许为了测试方便移除确认层、最近动作结果、审计记录面板

## 验收视觉标准

1. Runtime Console 视觉语言与 Phase 3 保持一致
2. 错误提示、空状态、loading 状态有统一样式，不像临时 debug 输出
3. audit / parse / smoke 状态可见，但不过度喧宾夺主
4. 无 emoji 图标、无默认系统字体最终态、无新增风格漂移
