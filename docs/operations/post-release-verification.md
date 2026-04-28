# Post-Release Verification Guide

> 最后更新：2026-04-28
> 适用版本：Runtime V3.2+

本文档定义 ClaudeFlow 发布后的最小验证链，确保关键主链正常运行。

---

## 最小验证链概述

发布后必须执行以下验证链，确认核心功能正常运行：

```
Step 1: Runtime Smoke (7 端点)
Step 2: Health Check (服务可达性)
Step 3: Governance 入口 (可选，有治理任务时)
```

---

## Step 1: Runtime Smoke 验证

**命令**:
```bash
PYTHONPATH=src python3 scripts/runtime_smoke.py
```

**覆盖端点**:
| 端点 | 说明 | 验证内容 |
|------|------|----------|
| `/api/runtime/status` | 运行时总览 | repo_path/active_sessions/driver_name 字段 |
| `/api/runtime/sessions` | session 列表 | 返回数组结构 |
| `/api/session/{id}/events-list` | session 事件 | events 数组 |
| `/api/runtime/plan` | 调度计划 | tasks 数组 |
| `/api/runtime/dispatch` | dispatch 端点 | dispatch_result 结构 |
| `/api/runtime/action-audit` | 审计记录 | records 数组 |
| `/health` | 健康检查 | status=healthy |

**通过标准**:
- 输出包含 `Total: 7 passed, 0 failed`
- 所有端点返回 200 状态码

**失败定位**:
```bash
PYTHONPATH=src python3 scripts/runtime_smoke.py 2>&1 | grep -i "fail"
```

---

## Step 2: Health Check 验证

**命令**:
```bash
curl http://localhost:8000/health
```

**预期输出**:
```json
{
  "status": "healthy",
  "version": "3.0.0"
}
```

**失败定位**:
- 服务未启动：检查 uvicorn 进程
- 端口冲突：检查 8000 端口占用

---

## Step 3: Governance 入口验证（可选）

当发布包含 Governance 任务时，验证治理入口可用性：

**前提条件**:
- **从仓库根目录执行**：所有命令必须在 `/path/to/claudeflow/` 根目录下运行
- **PYTHONPATH=src**：必须设置此环境变量，否则无法正确导入 `claudeflow` 模块

**命令**:
```bash
PYTHONPATH=src python3 -c "
from claudeflow.cli import main
import sys
sys.argv = ['claude', 'runtime', 'dispatch', '--governance-root', '.super-dev', '--phase-id', 'phase-5', '--json']
main()
"
```

**预期输出**:
- JSON 输出包含 `tasks` 数组
- 包含 `executor_type: claude` 或 `executor_type: codex`
- 包含 `dispatch_order` 字段

**说明**: `--governance-root` 和 `--phase-id` 参数仅在 `runtime dispatch` 子命令下可用。当前 CLI 模块入口需通过 `-c` 方式调用。

---

## Step 4: 统一门禁复跑（可选）

验证完整门禁链是否通过：

**命令**:
```bash
bash scripts/run-release-gates.sh
```

**注意**: 发布后验证不需要执行完整门禁链，仅需 Step 1-3。

---

## 验证结果判定

| 验证结果 | 说明 | 处理方式 |
|----------|------|----------|
| **passed** | Smoke 7 passed + health healthy | 发布成功 |
| **partial** | Smoke < 7 passed 但关键端点可用 | 记录到交付摘要，观察运行 |
| **failed** | 关键端点失败 或 health 不 healthy | 考虑回滚 |

**关键端点定义**:
- `/api/runtime/status` - 必须通过
- `/api/runtime/sessions` - 必须通过
- `/health` - 必须通过

---

## 验证命令速查

```bash
# 快速验证（推荐）
PYTHONPATH=src python3 scripts/runtime_smoke.py

# 服务可达性
curl http://localhost:8000/health

# 详细端点验证
PYTHONPATH=src python3 -c "
from fastapi.testclient import TestClient
from claudeflow.runtime.api import app
client = TestClient(app)
print(client.get('/api/runtime/status').json())
print(client.get('/api/runtime/sessions').json())
"

# 完整门禁（调试用）
bash scripts/run-release-gates.sh
```

---

## 参考

- [release-checklist.md](release-checklist.md) - 发布前检查清单
- [release-readiness.md](release-readiness.md) - 分层标准详情
- [rollback-contract.md](rollback-contract.md) - 回滚约定
- [delivery-summary-template.md](delivery-summary-template.md) - 交付摘要模板
- [testing-observability.md](../runtime/testing-observability.md) - 测试入口说明
- [runtime_smoke.py](../../scripts/runtime_smoke.py) - Smoke 测试脚本