# Release Checklist

> 最后更新：2026-04-28
> 适用版本：Runtime V3.2+

本文档定义 ClaudeFlow 发布前的检查清单，按顺序执行确保发布质量。

---

## 统一门禁入口

一键执行全部门禁：

```bash
scripts/run-release-gates.sh
```

该脚本按顺序执行 Gate 1-6，输出通过/失败汇总与排查建议。

---

## 发布前检查清单

### Phase 1: 前端验证

```bash
cd console && npm test -- --run
```

- [ ] 全部测试 passed
- [ ] 无功能性 FAIL 或 Error
- [ ] 无 lifecycle warning（A42 已收口）
- [ ] 无 action-audit fetch warning（A41 已收口）

**预期输出**:
```
X files X tests passed
Duration: ~1.5s
```

---

### Phase 2: Python 核心验证

```bash
PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/unit/test_runtime_manager.py tests/unit/test_phase_gate_service.py -v
```

- [ ] test_runtime_api.py 全部 passed
- [ ] test_cli.py 全部 passed
- [ ] test_runtime_manager.py 全部 passed
- [ ] test_phase_gate_service.py 全部 passed

**预期输出**:
```
X passed in X.XXs
```

---

### Phase 3: Java 测试验证

```bash
mvn test
```

- [ ] RuntimeClientTest 全部 passed
- [ ] RuntimeControllerTest 全部 passed
- [ ] BUILD SUCCESS 输出

**预期输出**:
```
Tests run: X, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

---

### Phase 4: Python 回归验证

```bash
PYTHONPATH=src python3 -m pytest tests/unit/ -v --ignore=tests/unit/governance/ --ignore=tests/unit/test_employee_pool.py --ignore=tests/unit/test_knowledge_retrieval.py --ignore=tests/unit/test_phase_reviewer.py --ignore=tests/unit/test_task_reviewer.py --ignore=tests/unit/test_progress_reporter.py
```

- [ ] 全部 passed（除 legacy 模块跳过）
- [ ] 无功能性 FAILED

**预期输出**:
```
X passed, X skipped (legacy modules)
```

---

### Phase 5: Runtime Smoke 验证

```bash
PYTHONPATH=src python3 scripts/runtime_smoke.py
```

- [ ] status endpoint passed
- [ ] sessions endpoint passed
- [ ] events-list endpoint passed
- [ ] plan endpoint passed
- [ ] dispatch endpoint passed
- [ ] action-audit endpoint passed
- [ ] health endpoint passed

**预期输出**:
```
Total: 7 passed, 0 failed
Smoke test PASSED
```

---

### Phase 6: 文档一致性验证

```bash
scripts/verify-doc-consistency.sh
```

- [ ] INDEX.md Phase 状态描述准确
- [ ] changelog.md Phase 记录完整
- [ ] pipeline-state.json 与文档口径一致

**预期输出**:
```
=== CONSISTENCY CHECK PASSED ===
```

---

### Phase 7: 交付摘要生成

```bash
cat docs/runtime/changelog.md | grep -A 10 "## 2026-04-27 Phase 4"
```

- [ ] changelog.md 包含完整 Phase 记录
- [ ] 每个任务变更文件列表完整
- [ ] 能力描述准确

---

## 发布决策标准

### release-ready 条件

所有 blocker 门禁通过：
- [ ] Gate 1-6 全部 ✓
- [ ] 无功能性回归
- [ ] 文档与状态一致

### not-ready 条件

任一 blocker 失败：
- Gate 1-6 任一失败
- 功能性回归未修复
- 文档与 pipeline-state 不一致

---

## Warning Budget 记录

发布时需记录以下环境级 warning（不阻断）：

| Warning | 来源 | 处理建议 |
|---------|------|----------|
| urllib3/LibreSSL | Python 3.9 + urllib3 v2 | 环境升级时解决 |
| Node localstorage | Vitest browser mock | 测试环境限制 |

---

## 发布后验证

发布后执行最小验证链，详见 [post-release-verification.md](post-release-verification.md)：

**最小验证链**:
```bash
# Step 1: Runtime Smoke (7 端点)
PYTHONPATH=src python3 scripts/runtime_smoke.py

# Step 2: Health Check
curl http://localhost:8000/health

# Step 3: Governance 入口（可选）
PYTHONPATH=src python3 -c "from claudeflow.cli import main; ..."
```

- [ ] Smoke 7 passed, 0 failed
- [ ] health endpoint 返回 healthy
- [ ] 关键端点可用（status/sessions/health）

---

## 参考

- [release-gate-matrix.md](release-gate-matrix.md) - 门禁矩阵详情
- [release-readiness.md](release-readiness.md) - 分层标准详情
- [post-release-verification.md](post-release-verification.md) - 发布后验证说明
- [rollback-contract.md](rollback-contract.md) - 回滚约定
- [delivery-summary-template.md](delivery-summary-template.md) - 交付摘要模板
- [testing-observability.md](../runtime/testing-observability.md) - 测试入口说明
- [changelog.md](../runtime/changelog.md) - 变更记录
- [verify-doc-consistency.sh](../../scripts/verify-doc-consistency.sh) - 文档一致性校验脚本