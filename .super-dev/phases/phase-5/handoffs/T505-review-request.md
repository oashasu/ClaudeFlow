# T505 Review Request (Round 2)

> 任务: 固化回滚约定与交付摘要模板
> 提交时间: 2026-04-28T08:35:00Z
> 执行者: Claude宿主
> 审查者: Governor

---

## 返工原因

T505 Round 1 返工原因：
1. 回滚锚点使用占位符 `<previous-stable-tag>`，仓库无 tag
2. smoke 错误日志使用 `/tmp/smoke_error.log`，真实日志是 `/tmp/gate5.log`
3. delivery summary Python 命令未用 PYTHONPATH=src 口径

---

## 返工内容

| 变更 | 原内容 | 新内容 |
|------|--------|--------|
| 回滚锚点 | `git checkout <previous-stable-tag>` | `git revert HEAD` 或 `git checkout main` |
| Smoke 错误日志 | `/tmp/smoke_error.log` | `/tmp/gate5.log` |
| 回滚说明 | 无 | 明确当前仓库无稳定 tag，推荐 revert/main |
| Gate 2 命令 | `pytest -v` | `PYTHONPATH=src python3 -m pytest ...` |
| Gate 4 命令 | `pytest tests/unit/` | `PYTHONPATH=src python3 -m pytest tests/unit/` |
| Gate 5 命令 | `runtime_smoke.py` | `PYTHONPATH=src python3 scripts/runtime_smoke.py` |
| Gate 6 命令 | `verify-doc-consistency.sh` | `scripts/verify-doc-consistency.sh` |

---

## 约束满足

| 约束 | 满足情况 |
|------|----------|
| 回滚条件必须可操作 | ✅ git revert HEAD / git checkout main 真实可执行 |
| 交付摘要模板必须承接 Python Console Java smoke 证据 | ✅ PYTHONPATH=src 口径与 release-gate-matrix.md 一致 |

---

## 真实命令验证

### 回滚路径

```bash
$ git revert HEAD
# 或
$ git checkout main
```

### Smoke 日志

```bash
$ cat /tmp/gate5.log | grep -i "fail"
```

### Python Gate 口径

```bash
$ PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/unit/test_runtime_manager.py tests/unit/test_phase_gate_service.py -v
```

---

## Acceptance Coverage

### A55 回滚约定

| 要求 | 覆盖情况 |
|------|----------|
| 文档明确说明何时触发回滚 | ✅ 4 个触发条件 |
| 明确回滚后需要重验的命令和主链 | ✅ 5 条重验命令 |

---

## 禁止行为检查

| 禁止行为 | 检查结果 |
|----------|----------|
| 只写回滚原则不写触发条件与复验命令 | ✅ 未违反 - 4 个触发条件 + 5 条重验命令 |
| 交付摘要模板脱离当前仓库证据结构 | ✅ 未违反 - PYTHONPATH 口径与 gate matrix 一致 |

---

## 自检清单

- [x] rollback_contract_documented
- [x] delivery_summary_template_added
- [x] review_ready
- [x] 约束：回滚条件可操作（git revert HEAD）
- [x] 约束：交付摘要承接证据（PYTHONPATH 口径）
- [x] 禁止行为未触发

---

## 请求 Governor Review

请验证以下内容：

1. A55: 回滚锚点是否真实可执行
2. A55: Smoke 日志是否引用真实文件
3. 约束：delivery summary 是否用 PYTHONPATH 口径
4. 禁止行为是否未触发

---

**Decision Request**: A55 是否 accepted?