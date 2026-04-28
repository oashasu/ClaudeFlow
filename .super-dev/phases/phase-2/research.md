# Phase 2 Research

## 阶段名称

- `phase-2`
- `质量门禁闭环`

## Phase 1 后的真实缺口

Phase 1 已完成：

1. 多宿主执行主链
2. `RuntimeTaskSpec` 单主模型
3. 治理任务包进入 dispatch 主链
4. CLI/API 宿主字段输出

但以下能力仍未闭环：

1. `implemented != accepted`
2. Worker 结果回收后仍缺少标准化 review artifact
3. review 失败后仍缺少自动生成 rework task 的能力
4. phase 层面仍缺少明确的 reopen / advance 逻辑
5. gate 结论仍未落成可审计的 gate report

## 本阶段目标

在现有 `.super-dev + runtime + governance` 基础上，补齐最小质量门禁闭环：

```text
dispatch
→ result collected
→ review-ready
→ governor review
→ accepted / rework_required
→ gate report
→ reopen / advance
```

## 非目标

本阶段明确不做：

1. 宿主预算 / quota 感知
2. `AGENTS.md / CLAUDE.md` 正则约束解析
3. Pipeline Console / UI 增强
4. Java/Spring 侧联动
5. 新建第二套 runtime / dispatcher / driver 主链

## 关键设计判断

1. review / gate 产物必须落盘，不以聊天记录为准
2. 返工任务必须复用现有 task package schema，而不是发明另一种返工对象格式
3. `pipeline-state.json` 仍是唯一阶段治理真相源
4. Governor 仍由 Codex 宿主承担，Claude 只实现代码

## 阶段完成定义

只有同时满足以下条件，Phase 2 才算完成：

1. Worker 完成后可进入结构化待审查状态
2. Governor 可写标准化 review artifact
3. review fail 可生成结构化 rework task package
4. review pass 可写 gate report 并驱动 phase advance / reopen
5. 无 blocker findings，且回归测试通过
