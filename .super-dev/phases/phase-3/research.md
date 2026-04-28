# Phase 3 Research

## 阶段名称

- `phase-3`
- `Runtime Console 与外部消费面收口`

## Phase 2 后的真实缺口

Phase 2 已完成：

1. Worker 结果回收进入 review-ready
2. Governor review artifact 标准化落盘
3. rework task 自动生成
4. gate report 与 phase advance / reopen 闭环
5. `pipeline-state.json` 与 phase 状态一致

但以下缺口仍然存在：

1. 质量门禁能力已经存在，但 Runtime Console 对这些能力的可见性和可操作性还不稳定
2. Python runtime 返回体虽已具备主路径能力，但前端和外部 HTTP 消费面的协议约束没有被强绑定
3. Java 控制面与 Python runtime 之间仍然呈现“并存但未收口”的状态
4. 当前工作区中最活跃的改动集中在 `console/`、`src/main/java/` 与 `runtime API` 消费层，说明下一个真实交付面不再是治理内核，而是消费层

## 本阶段目标

在不回退 Phase 1 / Phase 2 主链的前提下，把 ClaudeFlow 的治理与 runtime 能力稳定暴露给两类消费者：

```text
Python runtime / governance
→ 稳定协议
→ Runtime Console 可见、可操作、可审计
→ Java/HTTP 控制面可消费、可转发、可回放
```

## 本阶段优先级判断

### P0

1. Runtime Console 主链可读、可用、可验证
2. 高影响动作建立确认与审计可见性
3. 前后端共享的 runtime 协议边界固定

### P1

1. Java 控制面对 runtime 的消费路径收口
2. 旧任务流页面与 runtime 页面职责边界清晰
3. 文档与示例同步

## 本阶段范围

### In Scope

1. Runtime Console 结构重构
2. runtime action audit 与操作确认链
3. runtime schema / sample / parse 校验
4. Java `TaskController / TaskService` 与 runtime / console 的契约收口
5. 控制台入口、页面骨架、状态提示和错误回放体验

### Out of Scope

1. 新一轮治理状态机重写
2. 宿主预算 / quota 系统
3. RBAC 与复杂审批流
4. 新增第二套 console
5. 推翻现有 Vue 3 + Pinia + Spring Boot 架构

## 关键设计判断

1. Phase 3 必须把“治理能力已完成”转化为“消费面可稳定使用”，否则治理闭环只是内核能力，不算产品闭环
2. 前端和 Java 外部消费面都必须服从同一份 runtime 协议，不允许各自发明字段
3. Runtime Console 必须继续作为独立工作台存在，不能退回旧 Dashboard 混合堆叠模式
4. 当前仓库已有 `docs/specs/2026-04-24-runtime-*.md` 可直接继承，不需要另起一套平行设计

## 阶段完成定义

只有同时满足以下条件，Phase 3 才算完成：

1. Runtime Console 页面结构从单页堆逻辑收敛为状态驱动结构
2. `intervene / complete / fail` 建立确认与审计链
3. live payload 在进入视图前有显式 parse / validate
4. Java 控制面对 runtime 的入口边界清晰，至少能稳定消费核心对象
5. 文档、sample、schema、测试和运行路径保持一致
