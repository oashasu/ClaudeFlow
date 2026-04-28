# Phase 3 UIUX

## 结论

Phase 3 有独立 UI，且必须在实现前锁定控制台工作台的设计系统。

## 冻结的 UI 工具链

### 图标库

- `lucide-vue-next`

禁止：

- emoji
- 自造临时 SVG 占位

### 字体系统

- 主字体：`IBM Plex Sans`
- 等宽字体：`JetBrains Mono`

若本地未安装，可在实现时通过 Web 字体或等效可控方式接入，但不得退回默认系统字体直出作为最终交付。

### 设计 token system

统一使用 CSS variables，不允许在组件里散落硬编码主色：

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

视觉方向：

- 不是黑客终端风
- 不是紫粉 AI 模板
- 更接近“运营工作台 + 审计台”的克制工业感

### 组件生态

- 基于现有 Vue 3 + Pinia + 自有组件继续演进
- `RuntimeConsole.vue` 作为页面编排层
- `console/src/components/runtime/**` 作为展示层
- 新增 `console/src/composables/**` 承担状态获取和动作逻辑
- 必要时新增 `console/src/types/**` 与 `console/src/validators/**`

不引入新的重型组件库来覆盖现有结构。

## 页面骨架

Runtime Console 页面固定为五段式：

1. 顶部控制条
   - live/sample 模式切换
   - 刷新状态
   - 最后同步时间
   - 关键动作入口
2. 运行态总览
   - status metrics
   - blocked reason summary
3. 调度与解释区
   - plan
   - explain
   - dispatch result
4. session 主表
   - session rows
   - row actions
5. 右侧或下方 inspector
   - session detail
   - event stream
   - recent action audit

移动端策略：

- 页面退化为纵向堆叠
- session inspector 变为抽屉或折叠区
- 不在移动端保留双栏强布局

## 交互规则

1. `complete` / `fail` 必须先弹出确认层
2. `intervene` 提交前必须显示目标 task/session 摘要
3. parse/validate 失败时要显示结构化错误卡片，不能只留空白
4. 最近一次 action 结果必须固定可见，不能埋在深层弹窗
5. session 行动作要弱主次分层，避免所有按钮同权重

## 验收视觉标准

1. 页面层级清晰，能一眼区分“状态概览 / 调度解释 / session 操作 / 审计回放”
2. 字体、颜色、图标和 token 使用一致
3. 无 emoji 图标
4. 无默认系统字体最终态
5. 无紫粉渐变、无无差别卡片墙
