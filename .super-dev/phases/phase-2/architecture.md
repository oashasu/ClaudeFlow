# Phase 2 Architecture

## 总体方案

在现有模块上做增量扩展：

```text
src/claudeflow/runtime/
  manager.py
  governance_adapter.py

src/claudeflow/governance/
  workspace.py
  pipeline_state.py
  task_loader.py
  state_machine.py

+ review_artifact.py
+ review_queue.py
+ gate_report.py
+ rework_generator.py
+ phase_gate_service.py
```

## 模块职责

### 1. `review_artifact.py`

职责：

- 定义 review artifact 结构
- 写入 `.super-dev/phases/<phase-id>/reviews/<task-id>-review.md`
- 标准化：
  - review_status
  - decision
  - blocker / non-blocker findings

### 2. `review_queue.py`

职责：

- 接收 Worker 已完成结果
- 生成待审查索引或队列对象
- 保证 Governor 有稳定输入

### 3. `gate_report.py`

职责：

- 汇总 phase 下任务审查状态
- 写入 `.super-dev/phases/<phase-id>/gate-report.md`
- 标准化：
  - phase_status
  - accepted_count
  - rework_required_count
  - blocker_count
  - advance_allowed

### 4. `rework_generator.py`

职责：

- 读取原任务包和 review artifact
- 生成返工任务包
- 继承原任务关键约束
- 记录 `rework_round`

### 5. `phase_gate_service.py`

职责：

- 负责 reopen / advance 决策
- 更新 `pipeline-state.json`
- 驱动 phase 状态流转

## 数据流

```text
RuntimeManager.collect_session_result()
→ review_queue.write()
→ Governor review writes review artifact
→ rework_generator or gate_report
→ phase_gate_service updates pipeline-state
```

## 架构约束

1. 不新增第二套 runtime manager
2. review / gate / rework 必须复用现有 `.super-dev` 路径体系
3. 所有新对象都必须可从 phase/task ID 反查
