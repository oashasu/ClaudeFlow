# V3 Checkpoint版本快照优化

> **日期**: 2026-04-22
> **版本**: V3.0
> **问题来源**: 任务级版本回退需求 + 多工作空间管理

---

## 问题分析

### 现有Checkpoint的局限

```
┌─────────────────────────────────────────────────────────────┐
│  V2 Checkpoint现状                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  记录内容：                                                   │
│  • task_state: 任务执行状态字典                               │
│  • execution_context: 执行上下文字典                          │
│  • phase: 当前阶段                                           │
│                                                             │
│  缺失内容：                                                   │
│  • 代码仓库的版本快照（commit/分支）                           │
│  • 文档仓库的版本快照                                         │
│  • 涉及的文件列表（精准回退边界）                              │
│                                                             │
│  结果：                                                      │
│  • 无法回退到"那个时间点"的代码状态                            │
│  • 只能回退任务状态，代码改动需手动处理                         │
│  • 多Claude Code并行协作时无法精准隔离                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 用户需求

```
┌─────────────────────────────────────────────────────────────┐
│  期望的Checkpoint                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  场景1：任务跑偏回退                                          │
│  • 发现某个阶段改错了                                         │
│  • 回退到上一个checkpoint                                    │
│  • 代码和文档都恢复到那个时间点                                │
│                                                             │
│  场景2：多Claude Code协作                                     │
│  • Claude Code A 做 Phase1                                  │
│  • Claude Code B 做 Phase2                                  │
│  • A出问题时，回退只影响A的改动，B的改动保持                    │
│                                                             │
│  场景3：任意checkpoint切换                                    │
│  • 每个checkpoint对应一个代码分支                             │
│  • 可以切换到任何checkpoint查看当时的代码状态                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 工作空间结构

### 三类工作空间

```
sandbox/
├── tasks/                     # 需求文档仓库（GitHub）
│   └── 2026-04-22_xxx/        # 每个任务一个目录
│
├── workspaces/                # 公司生产项目
│   ├── hjly-common-service/   # 镜像仓库，本地可提交
│   ├── hjly-order-service/    # patch投递，不推远程
│   └── ...
│
├── personal/                  # 个人项目（GitHub）
│   ├── claudeflow/            # 直接推送
│   └── weather-spider/
│
└── labs/                      # 实验项目（私有仓库）
    ├── dubbo-3.3.6-src/       # 激进实验
    └── hjly-common-service-jdk21/
```

### 工作空间特性对比

| 工作空间 | Git操作 | 远程推送 | 敏感文件 | Checkpoint策略 |
|---------|---------|---------|---------|---------------|
| tasks/ | 直接提交 | GitHub推送 | 无 | 主分支commit |
| workspaces/ | 本地提交 | 不推送 | 有脱敏 | 任务分支commit |
| personal/ | 直接提交 | GitHub推送 | 无 | 任务分支commit |
| labs/ | 本地提交 | 私有仓库 | 可能有 | 任务分支commit |

---

## 现有数据结构

### V2 Checkpoint dataclass

```python
@dataclass
class Checkpoint:
    checkpoint_id: str           # 快照ID
    task_id: str                 # 任务ID
    phase: str                   # 当前阶段
    timestamp: datetime          # 时间戳
    task_state: Dict[str, Any]   # 任务状态字典
    execution_context: Dict[str, Any]  # 执行上下文字典
    filename: str                # checkpoint文件名
    checkpoint_format_version: str = "2.0"
```

### 序列化JSON

```json
{
  "checkpoint_id": "cp_abc123",
  "task_id": "task-001",
  "phase": "phase1",
  "timestamp": "2026-04-22T10:00:00",
  "task_state": { ... },
  "execution_context": { ... },
  "filename": "v_phase1_complete.json",
  "checkpoint_format_version": "2.0"
}
```

---

## V3 改动设计

### 改动对比表

| 字段 | V2 | V3 | 说明 |
|------|-----|-----|------|
| `checkpoint_id` | ✓ | ✓ | 保留 |
| `task_id` | ✓ | ✓ | 保留 |
| `phase` | ✓ | ✓ | 保留 |
| `timestamp` | ✓ | ✓ | 保留 |
| `task_state` | ✓ | ✓ | 保留 |
| `execution_context` | ✓ | ✓ | 保留 |
| `filename` | ✓ | ✓ | 保留 |
| `checkpoint_format_version` | "2.0" | "3.0" | 升级 |
| **`snapshots`** | - | ✓ | 新增：各仓库版本快照 |
| **`files_involved`** | - | ✓ | 新增：涉及的文件列表 |
| **`branches`** | - | ✓ | 新增：任务使用的分支映射 |

### 新增字段详细结构

```json
{
  // 现有字段（保留）
  "checkpoint_id": "cp_abc123",
  "task_id": "task-001",
  "phase": "phase1",
  "timestamp": "2026-04-22T10:00:00",
  "task_state": { ... },
  "execution_context": { ... },
  "filename": "v_phase1_complete.json",
  "checkpoint_format_version": "3.0",

  // 新增：各仓库版本快照
  "snapshots": {
    "tasks": {
      "repo_path": "/Users/claw/sandbox/tasks",
      "commit": "abc123def",
      "branch": "main"
    },
    "workspaces/hjly-common-service": {
      "repo_path": "/Users/claw/sandbox/workspaces/hjly-common-service",
      "commit": "def456abc",
      "branch": "task-001-phase1",
      "has_sensitive_files": true
    }
  },

  // 新增：涉及的文件列表（精准回退边界）
  "files_involved": {
    "tasks": [
      "2026-04-22_xxx/INDEX.md",
      "2026-04-22_xxx/spec.md"
    ],
    "workspaces/hjly-common-service": [
      "src/main/java/.../Foo.java",
      "src/main/java/.../Bar.java"
    ]
  },

  // 新增：任务使用的分支映射
  "branches": {
    "tasks": "main",
    "workspaces/hjly-common-service": "task-001-phase1"
  }
}
```

### 字段说明

| 新增字段 | 用途 | 示例 |
|---------|------|------|
| `snapshots` | 记录各仓库在checkpoint时的commit/分支 | 回退时切换到对应commit |
| `files_involved` | 记录本次checkpoint涉及的文件 | 精准回退（只恢复这些文件） |
| `branches` | 记录任务使用的分支 | 任务结束时清理临时分支 |

---

## 分支策略

### 各工作空间的分支策略

| 工作空间 | 任务开始 | Checkpoint创建 | 任务结束 |
|---------|---------|---------------|---------|
| tasks/ | 主分支 | 直接commit | 合并到main |
| workspaces/ | 创建任务分支 `task-xxx-phaseN` | 任务分支commit | patch投递后清理 |
| personal/ | 创建任务分支 | 任务分支commit | 合并后删除 |
| labs/ | 创建任务分支 | 任务分支commit | 按需保留或删除 |

### 分支命名规范

```
task-{任务ID}-{阶段}

示例：
task-001-phase1     # 任务001的Phase1分支
task-001-subtask-2  # 任务001的子任务2分支
task-002-phase0     # 任务002的Phase0拆分分支
```

### 多Claude Code协作的分支隔离

```
┌─────────────────────────────────────────────────────────────┐
│  并行协作场景                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  任务拆分：                                                   │
│  • Claude Code A: 负责service层                              │
│  • Claude Code B: 负责controller层                           │
│                                                             │
│  分支策略：                                                   │
│  • A在 task-001-phase1-service 分支工作                      │
│  • B在 task-001-phase1-controller 分支工作                   │
│                                                             │
│  文件分工：                                                   │
│  • A的files_involved: [.../service/*.java]                   │
│  • B的files_involved: [.../controller/*.java]                │
│                                                             │
│  回退隔离：                                                   │
│  • A出问题 → 只回退service层文件                              │
│  • B的改动不受影响                                            │
│                                                             │
│  合并时：                                                     │
│  • A合并 → B合并 → 处理冲突（如有）                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 脱敏机制兼容

### workspaces/ 脱敏机制

```
┌─────────────────────────────────────────────────────────────┐
│  脱敏机制                                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  敏感文件配置：config/sensitive-files.conf                   │
│  • WeixinConstant.java                                      │
│  • SecurityConstants.java                                   │
│  • ...                                                      │
│                                                             │
│  处理方式：                                                   │
│  1. clone后自动脱敏（sanitize_directory）                    │
│  2. 标记为 assume-unchanged（Git忽略改动）                    │
│  3. 切换分支后自动重新脱敏（post-checkout hook）              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Checkpoint与脱敏的兼容设计

```
┌─────────────────────────────────────────────────────────────┐
│  兼容设计                                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 创建Checkpoint时：                                        │
│     • 排除 assume-unchanged 标记的文件                        │
│     • files_involved 不包含敏感文件                           │
│     • snapshots.has_sensitive_files = true（标记）           │
│                                                             │
│  2. 回退Checkpoint时：                                        │
│     • 只恢复 files_involved 中的文件                          │
│     • 敏感文件保持当前状态（已脱敏）                            │
│     • 不执行敏感文件的checkout                                │
│                                                             │
│  3. 切换分支后：                                              │
│     • post-checkout hook 自动重新脱敏                         │
│     • 敏感文件恢复脱敏状态                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 实现要点

```python
def create_checkpoint(self, task_id, phase, ...):
    """创建checkpoint，排除敏感文件"""

    # 获取敏感文件列表
    sensitive_files = self._get_sensitive_files(workspace_path)

    # 获取改动文件列表（排除敏感文件）
    changed_files = self._get_changed_files(workspace_path)
    non_sensitive_files = [f for f in changed_files
                           if f not in sensitive_files]

    # 记录到files_involved
    checkpoint.files_involved[workspace] = non_sensitive_files

def rollback_checkpoint(self, checkpoint_id):
    """回退checkpoint，跳过敏感文件"""

    for workspace, files in checkpoint.files_involved.items():
        # 只恢复非敏感文件
        for file in files:
            git_checkout(checkpoint.snapshots[workspace].commit, file)

        # 敏感文件不处理，保持当前脱敏状态
```

---

## 回退流程

### 精准回退流程

```
┌─────────────────────────────────────────────────────────────┐
│  回退流程                                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  输入：target_checkpoint_id                                  │
│                                                             │
│  步骤1：加载checkpoint                                        │
│  • 读取 snapshots（各仓库commit）                             │
│  • 读取 files_involved（涉及的文件）                          │
│                                                             │
│  步骤2：逐仓库回退                                            │
│  • 切换到对应分支                                             │
│  • checkout对应commit                                        │
│  • 只恢复 files_involved 中的文件                             │
│                                                             │
│  步骤3：处理敏感文件（workspaces/）                            │
│  • 跳过敏感文件的checkout                                     │
│  • 触发 post-checkout hook                                   │
│  • 自动重新脱敏                                               │
│                                                             │
│  步骤4：恢复任务状态                                          │
│  • 恢复 task_state                                           │
│  • 恢复 execution_context                                    │
│                                                             │
│  步骤5：清理后续checkpoint                                    │
│  • 删除时间戳大于目标checkpoint的记录                          │
│  • 删除对应的临时分支（如有）                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 回退命令设计

```bash
# CLI命令
claudeflow checkpoint rollback <checkpoint_id>

# 或指定任务和阶段
claudeflow checkpoint rollback --task task-001 --phase phase1
```

---

## 实现清单

### 新增模块

| 模块 | 职责 | 文件 |
|------|------|------|
| RepoSnapshotCollector | 收集各仓库版本信息 | checkpoint/snapshot_collector.py |
| SensitiveFileFilter | 过滤敏感文件 | checkpoint/sensitive_filter.py |
| BranchManager | 任务分支管理 | checkpoint/branch_manager.py |

### 修改模块

| 模块 | 改动内容 | 文件 |
|------|----------|------|
| Checkpoint | 新增字段snapshots/files_involved/branches | checkpoint.py |
| CheckpointManager | 新增创建/回退逻辑 | checkpoint.py |
| CheckpointService | Java端同步更新 | CheckpointService.java |
| CheckpointEntity | Java实体新增字段 | CheckpointEntity.java |

### 版本兼容

```python
SUPPORTED_FORMAT_VERSIONS = ["1.0", "2.0", "3.0"]

def load_checkpoint(data):
    version = data.get("checkpoint_format_version", "1.0")

    if version == "3.0":
        # 加载V3格式（含snapshots）
        return CheckpointV3.from_dict(data)
    elif version == "2.0":
        # 加载V2格式
        return Checkpoint.from_dict(data)
    else:
        # 加载V1格式（向后兼容）
        return Checkpoint.from_dict(data)
```

---

## 验收标准

### 功能验收

- [ ] 创建checkpoint时正确记录各仓库commit
- [ ] files_involved正确排除敏感文件
- [ ] 回退时精准恢复指定文件
- [ ] 回退后敏感文件保持脱敏状态
- [ ] 多Claude Code协作时文件边界隔离

### 测试覆盖

- [ ] 单仓库checkpoint测试
- [ ] 多仓库checkpoint测试
- [ ] 敏感文件排除测试
- [ ] 精准回退测试
- [ ] 版本兼容测试（V1/V2/V3）

---

## 后续扩展

### 未来版本可考虑

| 版本 | 功能 | 说明 |
|------|------|------|
| V3.1 | 检出锁机制 | 文件锁定，防止并行冲突 |
| V3.2 | 增量快照 | 只记录diff，减少存储 |
| V3.3 | 快照压缩 | 压缩历史checkpoint |