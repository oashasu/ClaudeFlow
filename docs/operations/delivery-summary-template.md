# Delivery Summary Template

> 最后更新：2026-04-28
> 适用版本：Runtime V3.2+

本文档定义 ClaudeFlow Phase 交付摘要模板，承接 Python/Console/Java/smoke 证据结构。

---

## Delivery Summary 模板

```markdown
# Phase X Delivery Summary

> Phase: phase-X
> 交付时间: YYYY-MM-DDTHH:MM:SSZ
> Decision: release-ready / not-ready

---

## Gate Results

| Gate | 命令 | 结果 | 说明 |
|------|------|------|------|
| Gate 1 | Console: npm test -- --run | X tests passed / FAIL | 前端测试 |
| Gate 2 | Python Core: PYTHONPATH=src python3 -m pytest ... | X passed / FAIL | Runtime API/CLI/Manager |
| Gate 3 | Java: mvn test | BUILD SUCCESS / FAIL | Java 侧契约 |
| Gate 4 | Python Regression: PYTHONPATH=src python3 -m pytest tests/unit/ | X passed / FAIL | 回归测试 |
| Gate 5 | Smoke: PYTHONPATH=src python3 scripts/runtime_smoke.py | 7 passed / FAIL | 主链端点 |
| Gate 6 | Doc Consistency: scripts/verify-doc-consistency.sh | PASSED / FAIL | 文档一致性 |

---

## Warning Budget

| Warning | 来源 | 处理 |
|---------|------|------|
| urllib3/LibreSSL | Python 3.9 + urllib3 v2 | 记录，环境升级解决 |
| Node localstorage | Vitest browser mock | 记录，测试环境限制 |

---

## Test Evidence

### Python Core
```
$ PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/unit/test_runtime_manager.py tests/unit/test_phase_gate_service.py -v

X passed in X.XXs
```

### Console
```
$ cd console && npm test -- --run

X files X tests passed
Duration: ~X.Xs
```

### Java
```
$ mvn test

Tests run: X, Failures: 0, Errors: 0, Skipped: 0
[INFO] BUILD SUCCESS
```

### Smoke
```
$ PYTHONPATH=src python3 scripts/runtime_smoke.py

Total: 7 passed, 0 failed
Smoke test PASSED
```

---

## Acceptance Coverage

| Acceptance ID | 说明 | 覆盖情况 |
|---------------|------|----------|
| AX1 | ... | ✅ |
| AX2 | ... | ✅ |

---

## Decision

- blocker: Gate X-X 全部 PASSED ✓
- non-blocker: 文档措辞微调 (下一迭代)
- warning budget: urllib3 + localstorage (已记录)

Decision: **release-ready**
```

---

## Evidence Structure

交付摘要模板承接以下证据结构：

| 证据类型 | 来源 | 模板字段 |
|----------|------|----------|
| **Python 测试** | pytest tests/unit/ | Test Evidence > Python Core |
| **Console 测试** | npm test -- --run | Test Evidence > Console |
| **Java 测试** | mvn test | Test Evidence > Java |
| **Smoke 端点** | runtime_smoke.py | Test Evidence > Smoke |
| **Gate 结果** | run-release-gates.sh | Gate Results 表 |
| **Warning Budget** | 日志输出 | Warning Budget 表 |

---

## 使用说明

1. 复制模板到 `output/delivery-summary-phase-X.md`
2. 执行 `bash scripts/run-release-gates.sh` 填充 Gate Results
3. 执行各验证命令填充 Test Evidence
4. 填充 Acceptance Coverage（来自 acceptance.md）
5. Governor 基于填充后的摘要做出 release-ready/not-ready 决策

---

## 参考

- [release-readiness.md](release-readiness.md) - 分层标准详情
- [rollback-contract.md](rollback-contract.md) - 回滚约定
- [post-release-verification.md](post-release-verification.md) - 发布后验证说明
- [acceptance.md](../../.super-dev/phases/phase-X/acceptance.md) - Phase Acceptance 标准