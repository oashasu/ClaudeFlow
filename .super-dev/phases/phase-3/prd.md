# Phase 3 PRD

## 阶段定位

Phase 3 负责把已经完成的 runtime / governance 内核，交付为一个真实可消费的产品表面：Runtime Console + Java/HTTP 控制面。

## 用户故事

### US-1 Governor / Operator

作为 Governor 或操作员，我需要在 Runtime Console 中稳定查看 runtime 状态、session 列表、阻塞原因和最近动作结果，而不是依赖零散日志或 sample 数据猜测当前状态。

### US-2 Action 执行者

作为执行者，我在控制台触发 `intervene / complete / fail` 时，需要有确认步骤、结果回显和审计记录，避免误操作不可追溯。

### US-3 外部系统消费者

作为 Java/HTTP 外部消费方，我需要拿到稳定的 runtime 协议，而不是跟着前端实现细节漂移。

### US-4 维护者

作为维护者，我需要 Console、Python runtime、Java 控制面的职责边界清晰，以便后续继续迭代而不是让页面、接口和兼容层继续缠在一起。

## 范围

### In Scope

1. Runtime Console 结构重构与页面收口
2. runtime actions 的确认、反馈和审计记录
3. runtime 协议、schema、sample、前端 parse 校验
4. Java 控制面对 runtime / console 的契约清理
5. 对应测试、实现文档和使用说明同步

### Out of Scope

1. 新增权限系统
2. 重做旧任务流业务模型
3. 重做整个 Java 后端领域模型
4. 宿主预算、配额与成本治理
5. 新增移动端或第二套前端

## 功能要求

1. Runtime Console 必须能稳定展示：
   - runtime status
   - sessions
   - runnable / blocked / running
   - explain / dispatch 结果
   - 最近一次 action 结果
2. `complete` 和 `fail` 必须要求二次确认；`intervene` 至少显示目标摘要后再提交
3. action 成功或失败后，必须形成可查询记录
4. live payload 进入视图前必须完成 parse / validate；失败时必须明确提示
5. Java 控制层必须明确哪些接口直接服务旧任务流，哪些接口代理或消费 runtime 能力
6. 任何协议字段变化都必须同步更新：
   - `examples/*.schema.json`
   - `examples/*.sample.json`
   - `docs/runtime/changelog.md`
   - `docs/README.md`

## 质量围栏

1. 不允许在前端静默吞掉 runtime payload 错误
2. 不允许绕过确认直接执行高影响动作
3. 不允许让 Java 控制层和前端各自维护不同字段约定
4. 不允许用新的页面层把旧问题再包一层，而不处理职责分离
