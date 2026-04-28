# T504 Review Request (Round 3)

> 任务: 同步发布后验证说明与关键主链检查
> 提交时间: 2026-04-28T08:45:00Z
> 执行者: Claude宿主
> 审查者: Governor

---

## 返工原因

T504 Round 2 返工原因：文档命令和 handoff 证据命令路径分叉。

- 文档写的是 `-m claudeflow.cli`，但这条路径没有返回 JSON
- handoff 用的是 `-c "from claudeflow.cli import main..."`，这条路径稳定返回 JSON

---

## 返工内容

文档命令改为与证据命令一致的真实可工作路径：

**新文档命令**:
```bash
PYTHONPATH=src python3 -c "
from claudeflow.cli import main
import sys
sys.argv = ['claude', 'runtime', 'dispatch', '--governance-root', '.super-dev', '--phase-id', 'phase-5', '--json']
main()
"
```

---

## 真实命令验证（与文档一致）

```bash
$ PYTHONPATH=src python3 -c "from claudeflow.cli import main; import sys; sys.argv = ['claude', 'runtime', 'dispatch', '--governance-root', '.super-dev', '--phase-id', 'phase-5', '--json']; main()"

{
  "active_agents": 12,
  "available_slots": 999,
  "blocked": [],
  "blocked_count": 0,
  "runnable_count": 6,
  "tasks": [
    {
      "executor_type": "claude",
      "dispatch_order": 1,
      ...
    },
    ...
  ]
}
```

---

## Acceptance Coverage

### A54 发布后验证说明

| 要求 | 覆盖情况 |
|------|----------|
| 文档明确说明发布后最小验证链 | ✅ Step 1-3: Smoke + Health + Governance 入口 |
| 至少覆盖 runtime status、sessions、events、dispatch|audit 等关键读链 | ✅ Smoke 覆盖 7 端点 |
| 必须引用仓库内现有脚本或真实 API 命令 | ✅ 使用 `-c` 真实可工作 CLI 路径，与证据一致 |

---

## 禁止行为检查

| 禁止行为 | 检查结果 |
|----------|----------|
| 只写概念性验证步骤 | ✅ 未违反 - 命令可执行并返回 JSON |
| 用 sample 静态数据替代运行态验证链 | ✅ 未违反 - 使用真实 CLI + TestClient |

---

## 自检清单

- [x] post_release_verification_documented
- [x] key_mainline_checks_defined (7 端点)
- [x] review_ready
- [x] 约束：引用真实 CLI 命令
- [x] 约束：文档命令与证据命令一致
- [x] 禁止行为未触发

---

## 请求 Governor Review

请验证以下内容：

1. A54: 文档命令是否与证据命令路径一致
2. 约束：是否引用仓库内真实可工作命令
3. 禁止行为是否未触发

---

**Decision Request**: A54 是否 accepted?