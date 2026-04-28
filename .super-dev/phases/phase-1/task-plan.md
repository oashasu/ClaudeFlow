# Phase 1 Task Plan

## 执行顺序

1. `T101` RuntimeDriver 抽象
2. `T102` ClaudeDriver 收敛与 registry
3. `T103` CodexDriver 最小路径
4. `T104` governance task → runtime dispatch 适配
5. `T105` RuntimeManager / Session Index 宿主化
6. `T106` CLI / API 治理入口增强
7. `T107` 测试与回归

## 依赖关系

- `T102` 依赖 `T101`
- `T103` 依赖 `T101`
- `T104` 依赖 `T101`
- `T105` 依赖 `T102 + T103 + T104`
- `T106` 依赖 `T104 + T105`
- `T107` 依赖 `T102 ~ T106`

## 宿主分配策略

- 主实现任务默认交 `claude`
- 精准测试/CLI 修正任务允许交 `codex`
- 同一任务不得由同一宿主“自实现 + 自签发 accepted”
- 当前阶段剩余 `T106 / T107` 明确交 `claude` 实现，`codex` 仅保留 Governor 审查权

## 当前返工决策

当前审查要求在 Phase 1 内完成两项返工，不得推迟到下一阶段：

1. `runtime` 默认主链必须宿主化，不能继续保留写死 `claude` 的默认 dispatch 主路径。
2. `RuntimeTaskSpec` 必须成为主链任务模型，`WorkerTaskSpec` 最多只允许作为短期兼容输入。

## 返工顺序

1. `T108` 主链宿主化返工
2. `T109` RuntimeTaskSpec 主模型迁移
3. 原 `T106` CLI / API 治理入口增强
4. 原 `T107` 测试与回归

## 返工依赖

- `T108` 依赖 `T101 + T102 + T103 + T104 + T105`
- `T109` 依赖 `T108`
- `T106` 依赖 `T108 + T109`
- `T107` 依赖 `T108 + T109 + T106`

## 不属于本阶段

- 自动 review / rework / advance
- Java 调度链改造
- UI / console 增强
