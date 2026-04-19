# 强制checkpoint机制设计（V2追加）

> **日期**: 2026-04-19
> **版本**: V2.04
> **问题来源**: 被动触发总结不可靠，system消息可能被忽略

---

## 问题分析

### 被动触发的问题

```
┌─────────────────────────────────────────────────────────────┐
│  被动触发链                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  方案：监控上下文 → 提示总结                                 │
│                                                             │
│  问题1：触发时机不准确                                        │
│  • 工具调用计数偏差大                                        │
│  • 文件大小≠上下文大小                                       │
│                                                             │
│  问题2：system消息可能被忽略                                  │
│  • 上下文大时Claude注意力分散                                │
│  • system消息权重较低                                        │
│  • Claude可能贪婪继续执行                                    │
│                                                             │
│  问题3：总结质量不确定                                        │
│  • Claude可能敷衍总结                                        │
│  • 总结可能不进入下一阶段上下文                               │
│                                                             │
│  结果：                                                      │
│  • 关键信息可能丢失                                          │
│  • 下一阶段可能重复犯错                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 与Git commit的类比

```
┌─────────────────────────────────────────────────────────────┐
│  Git commit vs Hermes checkpoint                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Git commit：                                                │
│  • 不是"提醒你commit"                                        │
│  • 而是"必须commit才能继续下一步工作"                         │
│  • 强制性的流程节点                                          │
│                                                             │
│  Hermes checkpoint（被动）：                                  │
│  • "提示你总结一下"                                          │
│  • Claude可能忽略                                           │
│  • 可能继续贪婪执行                                          │
│  → 不可靠                                                   │
│                                                             │
│  Hermes checkpoint（强制）：                                  │
│  • "必须总结才能继续执行下一子任务"                           │
│  • 强制性的流程节点                                          │
│  • 总结完成后才能注入下一prompt                              │
│  → 可靠                                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 方案设计

### 强制checkpoint流程

```
┌─────────────────────────────────────────────────────────────┐
│  强制checkpoint流程                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  子任务执行                                                  │
│      ↓                                                      │
│  Hermes检测子任务完成                                        │
│      ↓                                                      │
│  强制注入prompt（阻塞式）：                                   │
│      "子任务已完成，请用以下格式总结（150字以内）：             │
│       - 关键决策：...                                        │
│       - 产出文件：...                                        │
│       - 遇到的问题：...                                      │
│       总结完成后将进入checkpoint并继续下一子任务。"           │
│      ↓                                                      │
│  Claude输出总结（必须输出才能继续）                           │
│      ↓                                                      │
│  Hermes保存checkpoint                                       │
│      ↓                                                      │
│  清空/压缩当前上下文                                         │
│      ↓                                                      │
│  注入checkpoint摘要 + 下一子任务prompt                        │
│      ↓                                                      │
│  Claude继续执行                                              │
│                                                             │
│  关键点：                                                     │
│  • 不是"提醒总结"，而是"必须总结才能继续"                     │
│  • 总结是阻塞式的流程节点                                    │
│  • 总结完成后上下文才清空                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 与被动触发的对比

| 维度 | 被动触发 | 强制checkpoint |
|------|----------|----------------|
| 触发方式 | system消息提示 | 阻塞式prompt注入 |
| 是否可忽略 | 可能忽略 | 必须响应才能继续 |
| 时机控制 | 不准确 | 准确（子任务完成时） |
| 上下文处理 | 可能不清空 | 强制清空/压缩 |
| 可靠性 | 低 | 高 |

---

## 实现要点

### 子任务完成检测

```python
# hermes/core/scheduler.py

class Scheduler:
    def detect_subtask_completion(self, task_id, tool_results):
        """检测子任务完成"""
        
        # 检测标志：
        # 1. 测试通过（pytest输出）
        # 2. 文件创建完成（Write工具）
        # 3. 显式完成标记（用户声明）
        
        if self._tests_passed(tool_results):
            return True
        
        if self._file_created(tool_results) and self._no_pending_edits(task_id):
            return True
        
        return False
    
    def _tests_passed(self, tool_results):
        """检测测试通过"""
        for result in tool_results:
            if 'pytest' in result.get('command', ''):
                if 'passed' in result.get('output', ''):
                    return True
        return False
```

### 强制总结注入

```python
# hermes/core/checkpoint_manager.py

class CheckpointManager:
    def trigger_forced_summary(self, task_id, subtask_id):
        """触发强制总结（阻塞式）"""
        
        summary_prompt = f"""
        子任务 {subtask_id} 已完成。
        
        请用以下格式总结本子任务工作（控制在150字以内）：
        
        ## 子任务总结
        - 关键决策：...
        - 产出文件：...
        - 遇到的问题及解决方案：...
        
        总结完成后，将进入checkpoint并继续下一子任务。
        """
        
        # 强制注入prompt（阻塞式，必须响应）
        return {
            "type": "forced_summary_prompt",
            "prompt": summary_prompt,
            "block_until_response": True
        }
```

### 上下文清空/压缩

```python
# hermes/core/context_manager.py

class ContextManager:
    def clear_for_next_subtask(self, task_id, checkpoint_summary):
        """清空上下文，只保留必要的checkpoint摘要"""
        
        # 清空当前上下文（除了checkpoint摘要）
        new_context = {
            "checkpoint_summary": checkpoint_summary,  # 150字
            "next_subtask_prompt": self.get_next_subtask_prompt(task_id)
        }
        
        return new_context
    
    def get_checkpoint_summary(self, task_id, subtask_id):
        """获取checkpoint摘要（用于注入下一子任务）"""
        
        # 从checkpoint读取总结
        checkpoint = self.load_checkpoint(task_id, subtask_id)
        
        # 提取摘要（150字）
        summary = checkpoint['summary']
        
        return f"[checkpoint] {summary}"
```

---

## Checkpoint内容结构

```
┌─────────────────────────────────────────────────────────────┐
│  Checkpoint JSON结构                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  {                                                          │
│    "checkpoint_version": "v_sub_1_complete",                │
│    "checkpoint_type": "subtask_complete",                   │
│    "task_id": "task_001",                                   │
│    "subtask_id": "sub_1",                                   │
│    "subtask_name": "状态机模块设计",                         │
│    "timestamp": "2026-04-19T10:30:00",                      │
│                                                             │
│    "summary": {                                             │
│      "key_decisions": ["采用七状态模型"],                    │
│      "files_modified": ["state_machine.py"],                │
│      "issues_resolved": ["重试策略调整"],                    │
│      "tests_passed": 47                                     │
│    },                                                       │
│                                                             │
│    "artifacts": [                                           │
│      "hermes/core/state_machine.py",                        │
│      "tests/unit/test_state_machine.py"                     │
│    ],                                                       │
│                                                             │
│    "context_for_next": "状态机模块完成，采用七状态模型..."     │
│  }                                                          │
│                                                             │
│  关键字段：                                                  │
│  • summary：总结内容（150字）                                │
│  • artifacts：产出文件列表                                   │
│  • context_for_next：注入下一子任务的摘要                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 上下文控制策略

### 每个子任务的上下文构成

```
┌─────────────────────────────────────────────────────────────┐
│  子任务上下文构成                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  子任务N开始时的上下文：                                      │
│                                                             │
│  [系统prompt]（固定，~2K tokens）                            │
│  + [任务总目标]（~500 tokens）                               │
│  + [checkpoint1摘要]（~150 tokens）                          │
│  + [checkpoint2摘要]（~150 tokens）                          │
│  + ...                                                      │
│  + [checkpointN-1摘要]（~150 tokens）                        │
│  + [子任务N prompt]（~500 tokens）                           │
│                                                             │
│  总量：                                                      │
│  • 2K + 500 + (N-1)×150 + 500                               │
│  • N=7时：2K + 500 + 900 + 500 = ~4K tokens                 │
│                                                             │
│  子任务执行过程中的增长：                                     │
│  • 每次工具调用增加200-500 tokens                            │
│  • 50次工具调用后：~15K-25K tokens                           │
│                                                             │
│  子任务完成时：                                              │
│  • 强制总结 → checkpoint                                    │
│  • 清空执行过程的历史                                        │
│  • 只保留checkpoint摘要                                     │
│                                                             │
│  → 下一子任务开始时上下文回到~4K tokens                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 上下文增长曲线

```
┌─────────────────────────────────────────────────────────────┐
│  上下文变化曲线                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  时间轴：                                                    │
│  ├─ 子任务1开始：4K tokens                                  │
│  ├─ 子任务1执行中：增长到20K tokens                          │
│  ├─ 子任务1完成：强制checkpoint → 清空 →回到5K              │
│  ├─ 子任务2开始：5K tokens                                  │
│  ├─ 子任务2执行中：增长到20K tokens                          │
│  ├─ 子任务2完成：强制checkpoint → 清空 →回到6K              │
│  ├─ ...                                                     │
│  ├─ 子任务N开始：4K+(N-1)×150tokens                         │
│  ├─ 子任务N完成：任务结束                                    │
│                                                             │
│  特点：                                                      │
│  • 每个子任务上下文控制在20K以内                              │
│  • 不会无限增长                                              │
│  • 只累积checkpoint摘要（每条150字）                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

---

## 补充设计：显式完成标记格式

### 完成标记定义

```
Claude Code在子任务完成时输出固定标记：
# SUBTASK_COMPLETE

Hermes检测到此标记 → 立即触发强制checkpoint
```

### 标记使用方式

```python
# Hermes注入的prompt尾部

prompt = """
...
完成本子任务后，请输出以下标记：
# SUBTASK_COMPLETE

然后等待checkpoint指令。
"""
```

### 完成检测优先级

```python
# hermes/core/subtask_detector.py

def detect_subtask_completion(self, task_id, tool_results, assistant_output):
    """检测子任务完成（优先级排序）"""

    # 优先级1：显式标记
    if "# SUBTASK_COMPLETE" in assistant_output:
        return True, "explicit_marker"

    # 优先级2：测试通过
    if self._tests_passed(tool_results):
        return True, "tests_passed"

    # 优先级3：文件创建完成（需确认无pending edits）
    if self._file_created(tool_results) and self._no_pending_edits(task_id):
        return True, "file_created"

    return False, None
```

---

## 补充设计：Checkpoint版本兼容性

### 版本字段

```json
{
  "checkpoint_version": "v_sub_1_complete",
  "checkpoint_format_version": "2.0",  // 格式版本号
  ...
}
```

### 兼容性检查

```python
# hermes/core/checkpoint.py

SUPPORTED_FORMAT_VERSIONS = ["1.0", "2.0"]

def load_checkpoint(self, checkpoint_path):
    checkpoint = json.load(open(checkpoint_path))
    format_version = checkpoint.get("checkpoint_format_version", "1.0")

    if format_version not in SUPPORTED_FORMAT_VERSIONS:
        raise IncompatibleCheckpointError(
            f"Checkpoint format {format_version} not supported"
        )

    return checkpoint
```

### 版本升级处理

```
V1 checkpoint（无format_version字段）→ 默认为"1.0"→ 兼容加载
V2 checkpoint（有format_version="2.0"）→ 正常加载

未来升级：
• 新增字段向后兼容
• 删除字段需format_version升级
• 老版本Hermes拒绝加载新版本checkpoint
```

---

## 补充设计：Checkpoint文件命名规范

### 命名规则

```
tasks/{task_id}/checkpoint/
├── v_phase0_split_complete.json    # Phase0拆分完成
├── v_sub_1_complete.json           # 子任务1完成
├── v_sub_2_complete.json           # 子任务2完成
├── v_sub_3_complete.json           # 子任务3完成
├── v_phase1_complete.json          # Phase1完成
├── v_phase1_review.json            # Phase1复盘
└── v_task_complete.json            # 任务完成
```

### 版本号规则

```
v_{阶段}_{事件}

阶段：phase0, sub_1, sub_2, ..., phase1, task
事件：split_complete, complete, review

示例：
• v_sub_1_complete = 子任务1完成checkpoint
• v_phase1_review = Phase1复盘checkpoint
```

---

## 待实现模块（更新）

| 模块 | 文件 | 说明 |
|------|------|------|
| SubtaskCompletionDetector | `hermes/core/subtask_detector.py` | 子任务完成检测（含优先级） |
| CheckpointManager | `hermes/core/checkpoint.py` | 强制checkpoint逻辑（含版本兼容） |
| ContextManager | `hermes/core/context_manager.py` | 上下文清空/压缩 |
| CheckpointValidator | `hermes/core/checkpoint_validator.py` | checkpoint格式验证 |