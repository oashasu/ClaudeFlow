# Release Readiness 分层标准

> 最后更新：2026-04-28
> 适用版本：Runtime V3.2+

本文档定义 ClaudeFlow 发布决策的分层标准，明确 blocker / non-blocker / warning budget 的边界。

---

## 发布决策分层

| 级别 | 定义 | 判断标准 | 处理方式 |
|------|------|----------|----------|
| **blocker** | 功能性回归、主链断裂、文档状态不一致 | Gate 1-6 任一失败 | 发布前必须修复 |
| **non-blocker** | 文档瑕疵、次要警告 | 文档风格/措辞问题但不影响发布决策 | 可在下一迭代修复 |
| **warning budget** | 环境级噪音 | 日志输出但不影响功能 | 不阻断发布，记录到交付摘要 |
| **test log output** | 测试正常路径输出 | 测试通过但有日志级 ERROR | 不阻断发布，不影响判断 |

---

## Blocker 边界（必须修复）

以下情况属于 **blocker**，发布前必须修复：

### 功能性回归
- Gate 1-6 任一门禁测试失败
- 新增代码导致已验收主链回退
- API 契约变更导致前端调用失败

### 主链断裂
- Runtime smoke 7 个端点任一失败
- dispatch/plan/status/sessions 核心端点不可达
- Governance 入口无法调度任务

### 文档与状态严重不一致
- Gate 6 校验失败（INDEX.md/changelog.md/pipeline-state.json 三方口径不一致）
- pipeline-state.json 与实际代码状态冲突
- Phase 状态文档宣称 accepted 但门禁未通过

---

## Non-Blocker 边界（可后续修复）

以下情况属于 **non-blocker**，可在下一迭代修复：

- 文档风格或措辞问题（不影响发布决策，不触发 Gate 6）
- 次要测试警告（如 legacy 模块 numpy 依赖警告）
- 代码风格问题（不影响功能）

**注意**: Gate 6 校验的 Phase 状态一致性、INDEX.md/changelog.md/pipeline-state.json 三方口径一致属于 **blocker**，见 blocker 边界定义。

---

## Warning Budget 边界（不阻断）

以下 warning 类型属于 **warning budget**，不阻断发布：

### urllib3/LibreSSL Warning
- **来源**: Python 3.9 环境与 urllib3 v2 版本冲突
- **输出**: `NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+`
- **影响**: 仅日志噪音，不影响 API 功能
- **处理**: 记录到交付摘要，后续环境升级时解决

### Node localstorage Warning
- **来源**: Vitest 测试环境缺少 browser localStorage API
- **输出**: `localStorage is not defined` 或类似警告
- **影响**: 仅测试输出噪音，不影响测试结果
- **处理**: 记录到交付摘要

---

## Test Log Output 边界（不影响判断）

以下日志输出属于 **测试正常路径输出**，不属于 blocker 或 warning：

### Java 测试日志级 ERROR
- **来源**: RuntimeClientTest 正常测试路径打印 Connection refused
- **输出**: `ERROR com.claudeflow.client.RuntimeClient - Failed to call Runtime API: Connection refused`
- **判断**: 测试真实结果为 `Tests run: 41, Failures: 0, Errors: 0, Skipped: 0` + `BUILD SUCCESS`
- **影响**: 日志级 ERROR 不代表 Maven test 失败，Gate 3 基于 surefire 汇总判断

### Python 测试日志级 Warning
- **来源**: urllib3 导入时打印的环境警告
- **判断**: 测试真实结果为 `X passed in X.XXs`，无 FAILED/ERROR
- **影响**: 日志级 Warning 不代表 pytest 失败

---

## Release Readiness 决策流程

### Step 1: 执行 Gate 1-6
```bash
scripts/run-release-gates.sh
```

### Step 2: 检查 blocker 边界
- Gate 1-6 全部 PASSED → 继续 Step 3
- 任一 Gate FAILED → **not-ready**，修复 blocker

### Step 3: 记录 warning budget
检查以下 warning 是否存在：
- urllib3/LibreSSL warning → 记录到交付摘要
- Node localstorage warning → 记录到交付摘要
- Java 日志级 ERROR → 不记录（测试正常路径）

### Step 4: 决策
- blocker 全部通过 + warning budget 已记录 → **release-ready**
- blocker 任一失败 → **not-ready**

---

## Governor 引用约定

Governor review 时应引用本文档作为分层基线：

```
Blocker check: Gate 1-6 PASSED ✓
Non-blocker: 文档措辞微调 (下一迭代)
Warning budget: urllib3 + localstorage (已记录)
Test log output: Java RuntimeClient ERROR (正常测试路径，不影响)
Decision: release-ready
```

**注意**: 若 Gate 6 失败（文档状态不一致），应判定为 blocker，需修复后重新提交。

---

## 参考

- [release-gate-matrix.md](release-gate-matrix.md) - 门禁矩阵详情
- [release-checklist.md](release-checklist.md) - 发布前检查清单
- [post-release-verification.md](post-release-verification.md) - 发布后验证说明
- [rollback-contract.md](rollback-contract.md) - 回滚约定
- [delivery-summary-template.md](delivery-summary-template.md) - 交付摘要模板
- [run-release-gates.sh](../../scripts/run-release-gates.sh) - 统一门禁入口