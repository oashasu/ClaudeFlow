# Rollback Contract

> 最后更新：2026-04-28
> 适用版本：Runtime V3.2+

本文档定义 ClaudeFlow 发布后的回滚触发条件、回滚步骤与重验命令。

---

## 回滚触发条件

以下情况必须触发回滚：

| 触发条件 | 检查方法 | 说明 |
|----------|----------|------|
| **功能性回归** | Gate 1-6 任一失败 | 发布后 runtime_smoke 7 端点任一失败 |
| **主链断裂** | 关键端点不可达 | status/sessions/health 返回非 200 或错误 |
| **数据丢失风险** | audit 记录异常 | action-audit 端点返回空或异常结构 |
| **服务不稳定** | 进程频繁崩溃 | uvicorn 进程退出 > 3 次/小时 |

---

## 回滚步骤

### Step 1: 确认回滚决策

```bash
# 确认触发条件存在
PYTHONPATH=src python3 scripts/runtime_smoke.py

# 若 Smoke 失败，确认是否为功能性回归
cat /tmp/gate5.log | grep -i "fail"
```

**决策规则**:
- Smoke 7 passed → 不回滚
- 关键端点失败 → 回滚
- 非关键端点失败 → 观察后决策

### Step 2: 执行回滚

```bash
# 回滚到上一个稳定版本（推荐：回滚最近提交）
git revert HEAD

# 或回滚到 main 分支稳定状态
git checkout main

# 重新部署
PYTHONPATH=src python3 -m claudeflow.runtime.api
```

**注意**: 当前仓库没有稳定 tag，推荐使用 `git revert HEAD` 或 `git checkout main` 作为回滚路径。

### Step 3: 重验主链

回滚后必须执行以下重验命令：

```bash
# Step 3.1: Python 核心验证
PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/unit/test_runtime_manager.py tests/unit/test_phase_gate_service.py -v

# Step 3.2: Console 验证
cd console && npm test -- --run

# Step 3.3: Java 验证
mvn test

# Step 3.4: Smoke 验证
PYTHONPATH=src python3 scripts/runtime_smoke.py

# Step 3.5: Health 验证
curl http://localhost:8000/health
```

---

## 重验主链清单

回滚后必须确认以下主链正常：

| 主链 | 重验命令 | 通过标准 |
|------|----------|----------|
| **Python 核心** | pytest tests/unit/test_runtime_api.py ... | X passed |
| **Console** | npm test -- --run | X tests passed |
| **Java** | mvn test | BUILD SUCCESS |
| **Smoke 7 端点** | runtime_smoke.py | 7 passed, 0 failed |
| **Health** | curl /health | status: healthy |

---

## 回滚后交付决策

回滚完成后，Governor 应重新做出交付决策：

```
Rollback verification:
- Python core: X passed ✓
- Console: X passed ✓
- Java: BUILD SUCCESS ✓
- Smoke: 7 passed ✓
- Health: healthy ✓

Decision: rollback-complete, release-ready
```

---

## 参考

- [release-readiness.md](release-readiness.md) - 分层标准详情
- [post-release-verification.md](post-release-verification.md) - 发布后验证说明
- [release-gate-matrix.md](release-gate-matrix.md) - 门禁矩阵详情