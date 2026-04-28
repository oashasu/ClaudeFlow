# Phase 4 PRD

## 阶段定位

Phase 4 负责收口 Runtime Console 的测试质量与可观测性，把 Phase 3 的功能交付固化为稳定、低噪音、可定位的问题检测能力。

## 用户故事

### US-1 Governor / Reviewer

作为 Governor 或审核者，我需要在复跑前端与 runtime 门禁时看到干净、可信的结果，而不是先人工区分哪些 warning 可以忽略。

### US-2 前端维护者

作为前端维护者，我需要一套稳定的测试 harness 和 mock 约定，这样在调整 composable 或视图层时，不会被偶发 warning、未隔离 fetch 或生命周期误用拖慢。

### US-3 Runtime 维护者

作为 runtime 维护者，我需要一条最小 smoke 主链，确认 status、sessions、events、action audit 这些核心契约在真实运行路径上没有断。

### US-4 后续交付负责人

作为后续 phase 的交付负责人，我需要知道 Phase 4 已经把“测试噪音”和“可观测性盲区”清掉，Phase 5 可以专注发布工程化而不是回头补前端质量地基。

## 范围

### In Scope

1. Runtime Console 前端测试 warning 清理
2. composable 测试 harness 标准化
3. action audit / runtime live data 测试隔离与错误路径断言
4. runtime smoke 最小闭环验证
5. 测试与可观测性文档同步

### Out of Scope

1. 新 UI 功能
2. 新 runtime 业务接口
3. Java/HTTP 发布流水线
4. 部署脚本、版本号策略、产物签名
5. release checklist 与 rollback runbook

## 功能要求

1. Runtime Console 相关前端测试默认运行时，不应再输出已知的 lifecycle warning 与 audit fetch warning
2. `useRuntimeLiveData`、`useRuntimeActions` 这类 composable 的测试必须通过标准 harness 挂载，不能直接裸调用导致生命周期告警
3. action audit 的获取失败、空记录、成功记录都必须有可断言的稳定测试覆盖
4. runtime smoke 必须覆盖至少以下链路：
   - runtime status
   - session list
   - session events
   - explain 或 dispatch 其中至少一条读链
   - action audit 或 action result 其中至少一条写后可观察链
5. 文档必须说明：
   - 测试层如何 mock runtime API
   - smoke 入口如何运行
   - 出现 warning / parse error / fetch error 时优先检查哪里

## 质量围栏

1. 不允许通过 `console.warn/error` 静默输出已知噪音后仍算测试完成
2. 不允许继续在 spec 内部散落重复 fetch mock 与手写 setup 包装
3. 不允许把 smoke 仅做成文档描述而没有实际入口
4. 不允许为了消音而删除真实失败路径断言
