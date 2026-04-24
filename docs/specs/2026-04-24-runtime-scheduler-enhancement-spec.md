# Runtime 调度器增强规格

> 状态：`pending`
>
> 优先级：`P2`

## 1. 目标

在当前最小调度器基础上，增强对真实多 Agent 编排场景的支持。

## 2. 重点问题

当前调度器已经支持：

- `depends_on`
- `priority`
- `max_concurrent`
- `write_paths`
- `reason_code`

但仍缺少：

- `shared_files` 的正式调度语义
- `IntegrationTask` 的特殊处理
- 上游失败后的重试/回流策略
- 在 `complete/fail` 之后对下一步可运行节点的更强建议

## 3. 功能要求

### 3.1 shared_files

`shared_files` 不能只是 task graph 上的静态字段，应进入调度决策，避免共享拼装文件被并发乱写。

### 3.2 IntegrationTask

必须允许显式标记集成任务，并对其应用更保守的串行策略。

### 3.3 失败回流

对于上游 `failed` 的任务，不能只有“阻塞”这一种处理方式，至少要支持：

- 标记等待人工处理
- 标记需要设计回流
- 后续为重试策略预留结构

### 3.4 下一步建议

在 `complete/fail` 后，runtime 至少应能给出：

- 新 runnable 节点
- 仍被阻塞的节点
- 阻塞原因摘要

## 4. 非目标

- 不在本阶段引入完整 DAG 可视化编辑器
- 不在本阶段实现复杂资源预算系统

## 5. 严格验收标准

1. `shared_files` 至少在一个正式调度分支里参与决策，不能继续只是占位字段。
2. `IntegrationTask` 具备明确规则，且相关任务不会与共享集成文件并发写入。
3. 上游失败场景下，系统输出不能只有单一 blocked 文本，至少要能区分失败阻塞与需要回流。
4. `complete/fail` 后必须能给出下一步任务建议或阻塞摘要。
5. 至少补充：
   - `shared_files` 调度测试
   - `IntegrationTask` 串行测试
   - 上游失败分流测试
   - explain/plan 行为测试
