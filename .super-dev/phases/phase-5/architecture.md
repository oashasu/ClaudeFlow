# Phase 5 Architecture

## 总体方案

Phase 5 采用“先固化发布门禁，再收口交付证据与回滚约定”的方案：

```text
python / console / java / smoke commands
        ↓
release gate matrix
        ↓
delivery checklist + evidence summary
        ↓
post-release verification
        ↓
rollback contract
```

## 模块职责

### 1. Release Gate 层

职责：

- 定义发布前必须通过的命令与顺序
- 把 blocker / non-blocker / warning budget 固化

主路径建议：

- `docs/operations/**`
- `scripts/**`（若需要统一入口）
- `.super-dev/phases/phase-5/**`

### 2. Delivery Evidence 层

职责：

- 汇总 Python / Console / Java / smoke 证据
- 形成 governor 可直接复核的交付摘要

主路径建议：

- `docs/runtime/changelog.md`
- `output/**` 或 `docs/operations/**`

### 3. Post-Release Verification 层

职责：

- 定义发布后最小可验证链路
- 避免“代码能跑，但发布后没人知道先验什么”

主路径建议：

- `docs/operations/**`
- `scripts/runtime_smoke.py` 或新增 release smoke 包装

### 4. Rollback Contract 层

职责：

- 定义回滚触发条件
- 明确回滚后需要重验的门禁

主路径建议：

- `docs/operations/**`

## 数据与验证流

### 1. 发布前门禁链

```text
console vitest
→ python regression
→ java tests
→ runtime smoke
→ document/state consistency check
→ release-ready decision
```

### 2. 发布后验证链

```text
service reachable
→ runtime status
→ sessions / events visibility
→ dispatch / audit visibility
→ release verification result
```

### 3. 回滚链

```text
blocker detected
→ rollback precondition matched
→ previous baseline restore
→ key gate rerun
→ service verification
```

## 架构约束

1. 不重写 Runtime 主代码来迁就发布流程
2. 统一入口若落到脚本，必须调用现有真实命令，而不是伪封装
3. 发布文档、governor review、pipeline-state 必须保持一致
4. 回滚说明必须基于当前仓库结构和已存在产物，不写脱离现实的流程
5. 若引入 release summary 模板，必须能被后续 phase 直接复用

## 阶段验收焦点

1. release readiness 是否可以被一致判断
2. 发布前后验证是否不再依赖口头经验
3. blocker 与环境噪音是否被清晰分层
