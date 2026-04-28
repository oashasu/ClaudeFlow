# Agent提炼机制设计（V2追加）

> **日期**: 2026-04-19
> **版本**: V2.02
> **问题来源**: Claude Code会话可能死循环刷屏，原始日志暴涨

---

## 问题分析

### 原始会话的问题

```
┌─────────────────────────────────────────────────────────────┐
│  死循环场景                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Claude Code输出：                                           │
│  {"type":"thinking", "content":"让我分析一下..."}             │
│  {"type":"thinking", "content":"让我分析一下..."}← 重复      │
│  {"type":"thinking", "content":"让我分析一下..."}← 死循环    │
│  ...重复100次...                                            │                                                             │
│                                                             │
│  影响：                                                       │
│  • 几分钟内日志暴涨几百MB                                     │
│  • WebSocket/SSE连接阻塞                                     │
│  • 磁盘空间耗尽                                              │
│  • 无价值内容占用存储                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 用户真正关心的内容

| 内容类型 | 是否需要 | 说明 |
|----------|----------|------|
| thinking全文 |否 | 大量重复，无价值 |
| 决策理由 | 是 | 为什么做这个决策 |
| 文件修改 | 是 | 改了什么文件 |
| 工具调用摘要 | 是 | 做了什么操作 |
| 遇到的问题 | 是 | 问题和解决方案 |

---

## 方案设计

### 分层提炼策略

```
┌─────────────────────────────────────────────────────────────┐
│  三层提炼                                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1：实时进度（无Agent，零成本）                         │
│  ─────────────────────────────────────────────             │
│  • 从工具调用直接提取"正在做什么"                             │
│  • Read xxx.py → "正在读取 xxx.py"                          │
│  • Edit xxx.py → "正在修改 xxx.py"                          │
│  • Bash pytest → "正在运行测试"                              │
│  • 推送到Vue显示进度                                         │
│                                                             │
│  Layer 2：阶段总结（主任务输出，进入上下文）                   │
│  ─────────────────────────────────────────────             │
│  • 阶段完成时主任务自己输出总结                               │
│  • Hermes强制注入prompt触发                                  │
│  • 总结内容进入下一阶段上下文（有价值）                        │
│  • 存入checkpoint                                           │
│                                                             │
│  Layer 3：阶段复盘（Haiku Agent，低成本）                     │
│  ─────────────────────────────────────────────             │
│  • 基于阶段总结做质量评估                                     │
│  • 异步执行，不阻塞主任务                                     │
│  • 输出改进建议、经验提炼                                     │
│  • 存入checkpoint                                           │
│                                                             │
│  Layer 4：任务复盘（任务完成时）                              │
│  ─────────────────────────────────────────────             │
│  • 汇总所有阶段总结和复盘                                     │
│  • Haiku做任务级别经验提炼                                    │
│  • 存入知识库                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 拒绝方案：记录原始会话

```
不记录原始会话的原因：
• 死循环问题无法解决
• 大体积内容无价值
• 存储成本高
• 分析成本高

替代方案：
• 只记录提炼后的内容
• 死循环内容自动被过滤
• 提炼日志几十KB，不是几百MB
```

---

## 提炼输出格式

### 实时进度（Layer 1）

```json
{
  "type": "tool_call_summary",
  "timestamp": "2026-04-19T10:30:00",
  "action": "正在读取 state_machine.py",
  "file": "hermes/core/state_machine.py"
}
```

### 阶段总结（Layer 2）

```json
{
  "type": "phase_summary",
  "phase": "概要设计",
  "timestamp": "2026-04-19T10:35:00",
  "summary": {
    "action": "完成状态机模块基础结构",
    "files_modified": ["hermes/core/state_machine.py"],
    "key_decisions": [
      "采用七状态模型而非五状态",
      "重试策略改为3次递增间隔"
    ],
    "tests_passed": 47,
    "issues_encountered": null,
    "progress": "状态机基础结构完成，测试全部通过"
  }
}
```

### 阶段复盘（Layer 3）

```json
{
  "type": "phase_review",
  "phase": "概要设计",
  "timestamp": "2026-04-19T10:36:00",
  "review": {
    "quality_score": 8,
    "strengths": ["测试覆盖率高", "设计清晰"],
    "improvements": [
      "重试间隔可考虑缩短为5→30→120秒"
    ],
    "lessons_learned": [
      "状态机设计应先画图再编码"
    ]
  }
}
```

### 任务复盘（Layer 4）

```json
{
  "type": "task_review",
  "task_id": "task_001",
  "timestamp": "2026-04-19T12:00:00",
  "review": {
    "overall_quality": 8,
    "phases_summary": [
      {"phase": "需求收集", "quality": 9},
      {"phase": "概要设计", "quality": 8},
      ...
    ],
    "key_lessons": [
      "复杂模块应拆成子任务执行",
      "前置拆分能显著降低上下文膨胀"
    ],
    "knowledge_extracted": [
      "状态机设计模式",
      "TDD工作流最佳实践"
    ]
  }
}
```

---

## 实现要点

### Layer 1：工具调用直接提取

```python
# hermes/core/tool_summary.py

def extract_action_from_tool(tool_name, tool_input):
    """从工具调用直接生成动作描述（无Agent调用）"""
    
    if tool_name == "Read":
        filename = tool_input['file_path'].split('/')[-1]
        return f"正在读取 {filename}"
    
    elif tool_name == "Edit":
        filename = tool_input['file_path'].split('/')[-1]
        return f"正在修改 {filename}"
    
    elif tool_name == "Write":
        filename = tool_input['file_path'].split('/')[-1]
        return f"正在创建 {filename}"
    
    elif tool_name == "Bash":
        cmd = tool_input['command']
        if 'pytest' in cmd:
            return "正在运行测试"
        elif 'git' in cmd:
            return "正在执行Git操作"
        return f"正在执行: {cmd[:30]}"
    
    elif tool_name == "Grep":
        return f"正在搜索: {tool_input['pattern'][:30]}"
    
    elif tool_name == "Glob":
        return f"正在查找文件: {tool_input['pattern']}"
    
    return f"正在执行 {tool_name}"
```

### Layer 2：阶段总结触发

```python
# hermes/core/scheduler.py

def on_phase_complete(self, task_id, phase):
    """阶段完成时强制触发总结"""
    
    # 强制注入prompt（必须总结才能继续）
    summary_prompt = f"""
    {phase}阶段已完成。
    请用以下格式总结本阶段工作（控制在200字以内）：
    
    ## 阶段总结
    - 关键决策：...
    - 产出文件：...
    - 遇到的问题及解决方案：...
    """
    
    # 通过prompt注入机制触发Claude Code输出总结
    # 总结内容自动进入checkpoint + 下一阶段上下文
```

### Layer 3：阶段复盘Agent

```python
# hermes/core/phase_reviewer.py

class PhaseReviewer:
    """异步阶段复盘（Haiku）"""
    
    async def review(self, task_id, phase, summary):
        prompt = f"""
        任务{task_id}的{phase}阶段总结：
        {summary}
        
        请评估：
        1. 质量（1-10分）
        2. 优点
        3. 可改进点
        4. 经验提炼
        
        输出JSON格式。
        """
        
        # 调用Haiku API（低成本）
        response = await call_haiku(prompt)
        return response
```

---

## 成本分析

| 提炼类型 | 频率 | 输入量 | 输出量 | 单次成本 | 任务总成本 |
|----------|------|--------|--------|----------|------------|
| 实时进度 | 每次工具调用 | 0 | 30字 | $0 | $0 |
| 阶段总结 | 8次/任务 | 0（主任务输出） | 200字 | $0 | $0 |
| 阶段复盘 | 8次/任务 | 200字 | 100字 | ~$0.01 | ~$0.08 |
| 任务复盘 | 1次/任务 | 2KB | 500字 | ~$0.02 | ~$0.02 |

**总成本：~$0.10/任务**

---

---

## 补充设计：提炼内容存储路径规范

### 存储目录结构

```
tasks/{task_id}/distilled/
├── tool_calls.json          # Layer1: 工具调用列表
├── thinking_filtered.json   # 过滤后的thinking
├── phase_summary.json       # Layer2: 阶段总结
├── phase_review.json        # Layer3: 阶段复盘
├── task_review.json         # Layer4: 任务复盘
└── alerts.json              # 告警记录
```

### 文件内容格式

#### tool_calls.json

```json
{
  "task_id": "task_001",
  "phase": "概要设计",
  "tool_calls": [
    {"timestamp": "...", "tool_name": "Read", "tool_input": {...}, "summary": "正在读取 xxx.py"},
    {"timestamp": "...", "tool_name": "Edit", "tool_input": {...}, "summary": "正在修改 xxx.py"}
  ],
  "total_count": 47
}
```

#### phase_summary.json

```json
{
  "task_id": "task_001",
  "phase": "概要设计",
  "timestamp": "2026-04-19T10:35:00Z",
  "summary": {
    "key_decisions": ["采用七状态模型"],
    "files_modified": ["state_machine.py"],
    "issues_resolved": ["重试策略调整"],
    "tests_passed": 47
  },
  "context_for_next": "状态机模块完成，采用七状态模型..."
}
```

---

## 补充设计：Claude Code .jsonl格式解析

### 解析入口

详见 [06_Claude_Code输出格式规范.md](06_Claude_Code输出格式规范.md)

### 解析流程

```
1. 定位.jsonl文件
   ~/.claude/projects/<project-id>/<session-id>.jsonl

2. 逐行解析JSON
   按type字段分类：user|assistant|tool_use|tool_result|system

3. 提取tool_use消息
   生成工具调用摘要（Layer1）

4. 过滤thinking内容
   去除死循环重复内容

5. 保存到distilled目录
```

---

## 补充设计：死循环检测阈值

### 检测规则

```python
# 同一thinking内容重复超过阈值视为死循环

DUPLICATE_THRESHOLD = 5  # 重复5次
MAX_THINKING_LENGTH = 500  # 单条最大长度
```

### 告警触发

```
检测到死循环 → WebSocket发送log_alert → Java → SSE推送Vue
→ 用户选择：继续等待 | 手动介入 | 取消任务
```

### 死循环告警格式

```json
{
  "type": "log_alert",
  "alert_level": "WARNING",
  "task_id": "task_001",
  "message": "检测到thinking死循环",
  "duplicate_content": "让我分析一下...",
  "duplicate_count": 12
}
```

---

## 待实现模块（更新）

| 模块 | 文件 | 说明 |
|------|------|------|
| ToolSummary | `hermes/core/tool_summary.py` | 工具调用摘要提取 |
| SessionParser | `hermes/core/session_parser.py` | .jsonl解析 |
| ThinkingFilter | `hermes/core/thinking_filter.py` | thinking过滤+死循环检测 |
| PhaseReviewer | `hermes/core/phase_reviewer.py` | 阶段复盘Agent |
| TaskReviewer | `hermes/core/task_reviewer.py` | 任务复盘Agent |
| SessionSummarizer | `hermes/core/session_summarizer.py` | 会话提炼总控 |