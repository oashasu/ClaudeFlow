# Phase 3 Claude 实现交接

## 角色边界

- `Claude` 负责实现 `T301 ~ T306`
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
- `../tasks/T301.yaml`
- `../tasks/T302.yaml`
- `../tasks/T303.yaml`
- `../tasks/T304.yaml`
- `../tasks/T305.yaml`
- `../tasks/T306.yaml`

## 实现总目标

把已完成的 runtime / governance 能力收口为真实可消费的产品表面：

```text
runtime protocol
→ Runtime Console 结构化消费
→ action confirmation + audit
→ Java/HTTP consumption boundary
→ docs + regression
```

## 执行顺序

1. 先做 `T301`，收口 Runtime Console 结构
2. 再做 `T302` 和 `T303`
3. `T304` 在协议与前端主链稳定后推进
4. `T305` 和 `T306` 收尾

## 必须满足

1. 不得新建第二套 Runtime Console 页面
2. 不得让 `RuntimeConsole.vue` 继续承担主要拉数和动作实现逻辑
3. `complete` / `fail` 必须有确认步骤
4. live payload parse 失败必须结构化可见
5. Java 层不得复制 Python runtime 状态机
6. 文档、sample、schema 与实现必须同步
7. 不得回退 Phase 1 / Phase 2 已验收能力

## UI 冻结约束

- 图标库: `lucide-vue-next`
- 字体: `IBM Plex Sans` + `JetBrains Mono`
- 颜色和视觉语言必须服从 `../uiux.md`
- 禁止 emoji 图标
- 禁止紫/粉渐变 AI 模板

## 本阶段不做

1. RBAC / 权限系统
2. 宿主预算 / quota
3. 新增第二套前端
4. 新一轮治理状态机重写

## 回传要求

- `changed_files`
- `summary`
- `test_evidence`
- `known_issues`
- 如有未完成项，必须逐条列出
