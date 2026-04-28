# Release Gate Matrix

> 最后更新：2026-04-28
> 适用版本：Runtime V3.2+

本文档定义 ClaudeFlow 发布前的质量门禁矩阵，包括门禁顺序、命令入口、通过标准和 blocker 分层。

---

## 统一门禁入口

一键执行全部门禁：

```bash
scripts/run-release-gates.sh
```

该脚本按固定顺序执行 Gate 1-6，失败时输出具体门禁编号与排查建议。

---

## 门禁顺序（固定）

发布前必须按以下顺序执行门禁：

| 序号 | 门禁名称 | 命令入口 | 通过标准 | blocker 级别 |
|------|----------|----------|----------|--------------|
| 1 | 前端测试 | `cd console && npm test -- --run` | 全部 passed，无功能性 error | **blocker** |
| 2 | Python 核心 | `PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/unit/test_runtime_manager.py tests/unit/test_phase_gate_service.py -v` | 全部 passed | **blocker** |
| 3 | Java 测试 | `mvn test` | 全部 passed，BUILD SUCCESS | **blocker** |
| 4 | Python 回归 | `PYTHONPATH=src python3 -m pytest tests/unit/ -v --ignore=tests/unit/governance/ --ignore=tests/unit/test_employee_pool.py --ignore=tests/unit/test_knowledge_retrieval.py --ignore=tests/unit/test_phase_reviewer.py --ignore=tests/unit/test_task_reviewer.py --ignore=tests/unit/test_progress_reporter.py` | 全部 passed | **blocker** |
| 5 | Runtime Smoke | `PYTHONPATH=src python3 scripts/runtime_smoke.py` | 7 passed, 0 failed | **blocker** |
| 6 | 文档一致性 | `scripts/verify-doc-consistency.sh` | INDEX.md/changelog.md/pipeline-state.json 三者口径一致 | **blocker** |

---

## 门禁详情

### Gate 1: 前端测试

**命令**:
```bash
cd console && npm test -- --run
```

**通过标准**:
- 输出包含 `X tests passed`
- 无 `FAIL` 或 `Error` 行
- 允许存在 Node/localstorage 环境级 warning（非 blocker）

**失败定位**:
```bash
# 检查具体失败测试
cd console && npm test -- --run 2>&1 | grep -i "fail"
```

**证据文件**: `console/tests/*.spec.ts`

---

### Gate 2: Python 核心

**命令**:
```bash
PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/unit/test_runtime_manager.py tests/unit/test_phase_gate_service.py -v
```

**通过标准**:
- 输出包含 `X passed`
- 无 `FAILED` 或 `ERROR` 行

**失败定位**:
```bash
# 检查具体失败测试
PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py -v --tb=short
```

**证据文件**: `tests/unit/test_runtime_api.py`, `tests/unit/test_cli.py`

---

### Gate 3: Java 测试

**命令**:
```bash
mvn test
```

**通过标准**:
- 输出包含 `BUILD SUCCESS`
- 无 `FAILURE` 或 `ERROR` 行
- RuntimeClientTest/RuntimeControllerTest 全部 passed

**失败定位**:
```bash
# 检查具体失败测试
mvn test 2>&1 | grep -i "failure"
```

**证据文件**: `pom.xml`, `src/test/java/com/claudeflow/**/*.java`

---

### Gate 4: Python 回归

**命令**:
```bash
PYTHONPATH=src python3 -m pytest tests/unit/ -v --ignore=tests/unit/governance/ --ignore=tests/unit/test_employee_pool.py --ignore=tests/unit/test_knowledge_retrieval.py --ignore=tests/unit/test_phase_reviewer.py --ignore=tests/unit/test_task_reviewer.py --ignore=tests/unit/test_progress_reporter.py
```

**通过标准**:
- 全部 passed
- legacy 模块（numpy 依赖）允许跳过

**失败定位**:
```bash
# 检查具体失败测试
PYTHONPATH=src python3 -m pytest tests/unit/ -v --tb=short 2>&1 | grep -i "failed"
```

**证据文件**: `tests/unit/*.py`

---

### Gate 5: Runtime Smoke

**命令**:
```bash
PYTHONPATH=src python3 scripts/runtime_smoke.py
```

**通过标准**:
- 输出包含 `Total: 7 passed, 0 failed`
- 覆盖端点：status/sessions/events-list/plan/dispatch/action-audit/health

**失败定位**:
```bash
# 检查具体失败端点
PYTHONPATH=src python3 scripts/runtime_smoke.py 2>&1 | grep -i "fail"
```

**证据文件**: `scripts/runtime_smoke.py`

---

### Gate 6: 文档一致性

**命令**:
```bash
scripts/verify-doc-consistency.sh
```

**通过标准**:
- `INDEX.md` 与 `changelog.md` Phase 状态描述一致
- `pipeline-state.json` phase 状态与文档口径一致
- 脚本输出 `CONSISTENCY CHECK PASSED`

**失败定位**:
```bash
# 检查文档差异
scripts/verify-doc-consistency.sh 2>&1 | grep -i "mismatch"
```

**证据文件**: `docs/INDEX.md`, `docs/runtime/changelog.md`, `.super-dev/pipeline-state.json`

---

## Blocker 分层

| 级别 | 定义 | 处理方式 |
|------|------|----------|
| **blocker** | 功能性回归、测试失败、主链断裂 | 发布前必须修复 |
| **non-blocker** | 文档瑕疵、次要测试警告 | 可在下一迭代修复 |
| **warning budget** | 环境级 warning（urllib3/LibreSSL） | 不阻断发布，记录到交付摘要 |
| **environment warning** | Node/localstorage、SSL 版本警告 | 不阻断发布，不影响功能 |

---

## Warning Budget 说明

以下 warning 类型不阻断发布：

1. **urllib3/LibreSSL warning**
   - 来源: Python 3.9 环境与 urllib3 v2 版本冲突
   - 影响: 仅日志噪音，不影响 API 功能
   - 处理: 记录到交付摘要，后续环境升级时解决

2. **Node localstorage warning**
   - 来源: Vitest 测试环境缺少 browser localStorage API
   - 影响: 仅测试输出噪音，不影响测试结果
   - 处理: 记录到交付摘要

---

## Governor 引用约定

Governor review 时应引用本矩阵作为门禁基线：

**统一入口执行**:
```bash
scripts/run-release-gates.sh
```

**逐门禁执行（调试用）**:
```
Gate 1: frontend X passed ✓
Gate 2: python core X passed ✓
Gate 3: java X passed ✓
Gate 4: python regression X passed ✓
Gate 5: smoke 7 passed ✓
Gate 6: doc consistency ✓
Warning budget: urllib3 + localstorage (记录)
Decision: release-ready
```

---

## 参考

- [release-readiness.md](release-readiness.md) - 分层标准详情
- [release-checklist.md](release-checklist.md) - 发布前检查清单
- [post-release-verification.md](post-release-verification.md) - 发布后验证说明
- [testing-observability.md](../runtime/testing-observability.md) - 测试入口详细说明
- [changelog.md](../runtime/changelog.md) - 实现变更记录
- [INDEX.md](../INDEX.md) - 项目索引与版本历史