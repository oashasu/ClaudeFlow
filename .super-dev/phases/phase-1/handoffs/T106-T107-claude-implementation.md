# Phase 1 T106/T107 Claude 实现交接

## 角色边界

- `Claude` 负责实现 `T106` 与 `T107`
- `Codex` 作为 `Governor` 只负责审查与阶段推进
- 不允许由 `Codex` 直接实现本轮代码

## 输入文档

- `../spec.md`
- `../acceptance.md`
- `../task-plan.md`
- `../tasks/T106.yaml`
- `../tasks/T107.yaml`

## 实现目标

### T106

- 为 CLI 增加治理入口：
  - 至少支持 `runtime dispatch --governance-root <root> --phase-id phase-1`
- 为 CLI/API 的 `plan / explain / dispatch` 输出补齐宿主字段：
  - `executor_type`
  - `driver_name`（已派发时）
- 不允许新增只存在于新命令中的平行运行链；必须复用现有 `RuntimeManager` 主链

### T107

- 补齐并回归验证以下测试口径：
  - `claude` 路径
  - `codex` 路径
  - `unsupported` 路径
  - CLI 治理入口
  - API 宿主字段输出
- 测试不得通过降低断言强度来换取通过

## 建议改动范围

### T106

- `src/claudeflow/cli.py`
- `src/claudeflow/runtime/api.py`
- 如确有必要，可最小调整 `src/claudeflow/runtime/manager.py`

### T107

- `tests/unit/test_phase1_multi_host.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_runtime_api.py`

## 必须满足的验收点

- `A08` 必须关闭：
  - CLI/API 输出可见 `executor_type`
  - 派发后可见 `driver_name`
- 不得要求 Governor 手工维护平行 task graph
- 不得回退 `T108/T109` 已完成的主链宿主化与单主模型决策

## 回传要求

- `changed_files`
- `summary`
- `test_evidence`
- 若存在未完成项，必须逐项列出，不得隐含跳过
