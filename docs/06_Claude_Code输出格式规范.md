# Claude Code输出格式规范（V2追加）

> **日期**: 2026-04-19
> **版本**: V2.06
> **问题来源**: 需要从Claude Code会话中提取工具调用和进度信息

---

## .jsonl文件格式

### 存储位置

```
~/.claude/projects/<project-id>/<session-id>.jsonl
```

### 单行JSON结构

```json
{
  "type": "user|assistant|tool_use|tool_result|system",
  "timestamp": "2026-04-19T10:30:00Z",
  "content": "...",
  "tool_name": "Read|Edit|Write|Bash|Grep|Glob|...",
  "tool_input": {...},
  "tool_result": "...",
  "thinking": "..."
}
```

### 消息类型说明

| type | 含义 | 关键字段 |
|------|------|----------|
| user | 用户输入 | content |
| assistant | Claude回复 | content, thinking |
| tool_use | 工具调用 | tool_name, tool_input |
| tool_result | 工具返回 | tool_result |
| system | 系统消息 | content |

---

## 工具调用提取规则

### 提取目标

从`tool_use`类型消息中提取：
- 工具名称
- 输入参数
- 时间戳

### 提取逻辑

```python
# hermes/core/session_parser.py

def extract_tool_calls(jsonl_path):
    """从.jsonl提取工具调用列表"""

    tool_calls = []
    with open(jsonl_path, 'r') as f:
        for line in f:
            msg = json.loads(line)
            if msg['type'] == 'tool_use':
                tool_calls.append({
                    'timestamp': msg['timestamp'],
                    'tool_name': msg['tool_name'],
                    'tool_input': msg['tool_input']
                })
    return tool_calls
```

### 工具调用摘要生成

```python
def generate_tool_summary(tool_call):
    """生成工具调用摘要（用于实时进度显示）"""

    tool_name = tool_call['tool_name']
    tool_input = tool_call['tool_input']

    if tool_name == 'Read':
        filename = tool_input['file_path'].split('/')[-1]
        return f"正在读取 {filename}"

    elif tool_name == 'Edit':
        filename = tool_input['file_path'].split('/')[-1]
        return f"正在修改 {filename}"

    elif tool_name == 'Write':
        filename = tool_input['file_path'].split('/')[-1]
        return f"正在创建 {filename}"

    elif tool_name == 'Bash':
        cmd = tool_input['command']
        if 'pytest' in cmd:
            return "正在运行测试"
        elif 'git' in cmd:
            return "正在执行Git操作"
        return f"正在执行: {cmd[:30]}"

    elif tool_name == 'Grep':
        pattern = tool_input['pattern'][:30]
        return f"正在搜索: {pattern}"

    elif tool_name == 'Glob':
        return f"正在查找文件: {tool_input['pattern']}"

    return f"正在执行 {tool_name}"
```

---

## Thinking内容过滤规则

### 问题：thinking可能死循环

```
{"type":"assistant", "thinking":"让我分析一下..."}
{"type":"assistant", "thinking":"让我分析一下..."} ← 重复
{"type":"assistant", "thinking":"让我分析一下..."} ← 死循环
```

### 过滤策略

```python
# hermes/core/thinking_filter.py

class ThinkingFilter:
    """Thinking内容过滤器"""

    # 死循环检测阈值
    DUPLICATE_THRESHOLD = 5  # 同一内容重复5次视为死循环
    MAX_THINKING_LENGTH = 500  # 单条thinking最大保留长度

    def filter_thinking(self, thinking_list):
        """过滤thinking列表，去除死循环内容"""

        filtered = []
        duplicate_count = {}

        for thinking in thinking_list:
            # 截断过长内容
            content = thinking[:self.MAX_THINKING_LENGTH]

            # 统计重复次数
            if content not in duplicate_count:
                duplicate_count[content] = 0
            duplicate_count[content] += 1

            # 超过阈值的不保留
            if duplicate_count[content] <= self.DUPLICATE_THRESHOLD:
                filtered.append(content)

        return filtered

    def detect_dead_loop(self, thinking_list):
        """检测是否存在死循环"""

        duplicate_count = {}
        for thinking in thinking_list:
            content = thinking[:self.MAX_THINKING_LENGTH]
            duplicate_count[content] = duplicate_count.get(content, 0) + 1
            if duplicate_count[content] > self.DUPLICATE_THRESHOLD:
                return True, content

        return False, None
```

---

## 会话内容提炼流程

### 输入

```
~/.claude/projects/<project-id>/<session-id>.jsonl
```

### 输出

```
tasks/<task_id>/distilled/
├── tool_calls.json      # 工具调用列表
├── thinking_filtered.json # 过滤后的thinking
├── phase_summary.json   # 阶段总结
└── phase_review.json    # 阶段复盘
```

### 提炼脚本

```python
# hermes/core/session_summarizer.py

class SessionSummarizer:
    """会话内容提炼器"""

    def summarize_session(self, jsonl_path, task_id, phase):
        """提炼会话内容"""

        # 1. 解析.jsonl
        messages = self.parse_jsonl(jsonl_path)

        # 2. 提取工具调用
        tool_calls = self.extract_tool_calls(messages)
        self.save(f"tasks/{task_id}/distilled/tool_calls.json", tool_calls)

        # 3. 过滤thinking
        thinking_list = self.extract_thinking(messages)
        filtered = self.thinking_filter.filter_thinking(thinking_list)
        self.save(f"tasks/{task_id}/distilled/thinking_filtered.json", filtered)

        # 4. 检测死循环
        dead_loop, content = self.thinking_filter.detect_dead_loop(thinking_list)
        if dead_loop:
            self.alert_dead_loop(task_id, content)

        # 5. 生成摘要（由主任务输出，不在这里）
        return {
            'tool_call_count': len(tool_calls),
            'thinking_count': len(filtered),
            'dead_loop_detected': dead_loop
        }
```

---

## 死循环告警机制

### 触发条件

```
同一thinking内容重复超过5次
```

### 告警输出

```json
{
  "type": "log_alert",
  "alert_level": "WARNING",
  "task_id": "task_001",
  "message": "检测到thinking死循环",
  "duplicate_content": "让我分析一下...",
  "duplicate_count": 12,
  "timestamp": "2026-04-19T10:35:00Z"
}
```

### 处理建议

```
WebSocket发送log_alert → Java → SSE推送Vue → 显示告警弹窗
用户可选择：
1. 继续等待（可能自动恢复）
2. 手动介入（注入prompt打断）
3. 取消任务
```

---

## 文件大小控制

### .jsonl文件监控

```python
# hermes/core/session_monitor.py

class SessionMonitor:
    """会话文件监控"""

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB阈值

    def check_file_size(self, jsonl_path):
        """检查文件大小"""

        size = os.path.getsize(jsonl_path)
        if size > self.MAX_FILE_SIZE:
            return {
                'alert': 'FILE_TOO_LARGE',
                'size': size,
                'threshold': self.MAX_FILE_SIZE
            }
        return None
```

### 超限处理

```
文件超过50MB → 告警 → 建议用户：
1. 强制checkpoint（清空上下文）
2. 拆分任务继续
3. 取消任务
```

---

## 待实现模块

| 模块 | 文件 | 说明 |
|------|------|------|
| SessionParser | `hermes/core/session_parser.py` | .jsonl解析 |
| ThinkingFilter | `hermes/core/thinking_filter.py` | thinking过滤 |
| SessionSummarizer | `hermes/core/session_summarizer.py` | 会话提炼 |
| SessionMonitor | `hermes/core/session_monitor.py` | 文件监控 |

---

## 与其他模块的集成

| 模块 | 使用方式 |
|------|----------|
| WebSocketClient | 提炼结果通过WebSocket推送 |
| ToolSummary | 使用extract_tool_calls生成摘要 |
| CheckpointManager | 阶段完成时触发提炼 |
| NodeSummarizer | 使用filtered thinking做复盘 |