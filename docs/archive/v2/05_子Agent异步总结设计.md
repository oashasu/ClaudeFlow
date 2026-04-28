# 子Agent异步总结设计（V2追加）

> **日期**: 2026-04-19
> **版本**: V2.05
> **问题来源**: 总结阻塞主任务执行

---

## 问题分析

### 主任务自己总结的问题

```
┌─────────────────────────────────────────────────────────────┐
│  主任务总结流程                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  主任务完成子任务                                            │
│      ↓                                                      │
│  Hermes注入强制总结prompt                                    │
│      ↓                                                      │
│  主任务输出总结（需要思考时间）                               │
│      ↓                                                      │
│  总结进入checkpoint                                         │
│      ↓                                                      │
│  继续下一子任务                                              │
│                                                             │
│  问题：                                                      │
│  • 总结需要主任务思考（占用主任务时间）                        │
│  • 阶段复盘需要主任务思考（更复杂）                            │
│  • 主任务不能立即继续                                        │
│                                                             │
│  更深层问题：                                                 │
│  • 总结内容进入主任务上下文 →膨胀                            │
│  • 复盘内容进入主任务上下文 → 膨胀                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 两类总结的区别

| 类型 | 目的 | 输入 | 输出 | 是否进入主任务上下文 |
|------|------|------|------|----------------------|
| 阶段总结 | 记录发生了什么 | 主任务自己的经历 | 150字总结 | **是**（下一阶段需要） |
| 阶段复盘 | 分析做得怎么样 | 阶段总结 | 评估+建议 | **否**（知识库用途） |

**关键洞察**：
- 阶段总结必须进入主任务上下文（下一阶段需要参考）
- 阶段复盘不应该进入主任务上下文（纯知识库用途）

---

## 方案设计

### 分离策略

```
┌─────────────────────────────────────────────────────────────┐
│  两种总结分开处理                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  阶段总结（主任务输出）：                                     │
│  ─────────────────────────────────────────────             │
│  • 主任务自己输出（必须）                                    │
│  • 进入下一阶段上下文（有价值）                              │
│  • Hermes强制注入prompt触发                                  │
│  • 阻塞式，必须响应才能继续                                  │
│                                                             │
│  阶段复盘（子Agent异步）：                                    │
│  ─────────────────────────────────────────────             │
│  • Haiku Agent异步执行                                      │
│  • 不进入主任务上下文（0膨胀）                                │
│  • 完成后系统级通知（不进对话历史）                           │
│  • 主任务不受影响，继续执行                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 异步复盘流程

```
┌─────────────────────────────────────────────────────────────┐
│  异步复盘流程                                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  主任务完成子任务                                            │
│      ↓                                                      │
│  Hermes强制注入总结prompt                                    │
│      ↓                                                      │
│  主任务输出总结                                              │
│      ↓                                                      │
│  ┌─────────────────┐                                        │
│  │ 分叉点│                                        │
│  └─────────────────┘                                        │
│      │                                                      │
│      ├─ 路径A（同步）：                                      │
│      │  • 总结进入checkpoint                                │
│      │  • 注入下一子任务prompt                               │
│      │  • 主任务继续执行                                    │
│      │                                                      │
│      ├─ 路径B（异步）：                                      │
│      │  • 启动Haiku复盘Agent                                │
│      │  • 读取阶段总结                                      │
│      │  • 输出评估和建议                                    │
│      │  • 存入checkpoint                                    │
│      │  • 系统级通知（不进对话历史）                         │
│      │                                                      │
│  两路径并行执行，互不阻塞                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 实现要点

### 异步复盘Agent

```python
# hermes/core/node_summarizer.py

class NodeSummarizer:
    """异步复盘Agent（Haiku）"""
    
    def __init__(self):
        self.haiku_client = HaikuClient()
    
    async def review_phase(self, task_id, subtask_id, summary):
        """异步复盘（不阻塞主任务）"""
        
        prompt = f"""
        任务{task_id}的{subtask_id}阶段总结：
        {summary}
        
        请评估：
        1. 质量（1-10分）
        2. 优点（最多3条）
        3. 可改进点（最多2条）
        4. 经验提炼（最多1条）
        
        输出JSON格式，控制在100字以内。
        """
        
        # 异步调用Haiku（不阻塞主任务）
        review = await asyncio.create_task(
            self.haiku_client.call(prompt)
        )
        
        # 存入checkpoint
        self.save_review(task_id, subtask_id, review)
        
        # 系统级通知（不进对话历史）
        self.notify_system(task_id, subtask_id)
    
    def notify_system(self, task_id, subtask_id):
        """系统级通知（0膨胀）"""
        # 通过WebSocket发送系统消息
        # Claude Code收到但不进入对话历史
        message = {
            "type": "system",
            "content": f"[checkpoint] {subtask_id}复盘已完成"
        }
        self.ws_client.send(message)
```

### 系统级通知vs用户消息

```
┌─────────────────────────────────────────────────────────────┐
│  两种消息类型的区别                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  user消息：                                                  │
│  • 进入对话历史 → 累积膨胀                                   │
│  • Claude必须响应                                            │
│                                                             │
│  system消息：                                                │
│  • 不进入对话历史 → 0膨胀                                    │
│  • Claude可以忽略                                            │
│  • 类似于"提示"，不是"指令"                                  │
│                                                             │
│  实现方式：                                                   │
│  • WebSocket发送 {"type": "system", "content": "..."}      │
│  • Claude Code收到但不记录到对话历史                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 主任务按需读取

```
┌─────────────────────────────────────────────────────────────┐
│  主任务如何使用复盘内容                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  复盘内容存入checkpoint                                      │
│  主任务收到系统级通知：                                       │
│      "[checkpoint] 复盘已完成"                               │
│                                                             │
│  主任务自己决定：                                             │
│  • 需要参考 →主动Read checkpoint文件                         │
│  • 不需要 → 继续执行                                         │
│                                                             │
│  上下文膨胀：                                                │
│  • 通知本身：0字（system消息不进历史）                        │
│  • 如果Claude主动读取：+100字（但这是有价值的）               │
│  • 如果Claude不读取：0字                                    │
│                                                             │
│  → Claude自己控制上下文膨胀                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 复盘内容结构

```
┌─────────────────────────────────────────────────────────────┐
│  复盘JSON结构                                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  {                                                          │
│    "review_type": "phase_review",                           │
│    "task_id": "task_001",                                   │
│    "subtask_id": "sub_1",                                   │
│    "timestamp": "2026-04-19T10:36:00",                      │
│                                                             │
│    "review": {                                              │
│      "quality_score": 8,                                    │
│      "strengths": [                                         │
│        "测试覆盖率高",                                       │
│        "设计清晰"                                            │
│      ],                                                     │
│      "improvements": [                                      │
│        "重试间隔可缩短为5→30→120秒"                          │
│      ],                                                     │
│      "lessons_learned": [                                   │
│        "状态机设计应先画图再编码"                             │
│      ]                                                      │
│    }                                                        │
│  }                                                          │
│                                                             │
│  存入路径：                                                  │
│  tasks/{task_id}/checkpoint/{subtask_id}_review.json        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 成本分析

| 操作 | Agent | 输入 | 输出 | 成本 |
|------|-------|------|------|------|
| 阶段复盘 | Haiku | 阶段总结（150字） | 评估（100字） | ~$0.01 |
| 任务复盘 | Haiku | 所有阶段总结+复盘（2KB） | 总评估（500字） | ~$0.02 |

**异步复盘总成本：~$0.10/任务**

---

---

## 补充设计：复盘触发读取机制

### 问题：system消息可能被忽略

```
system消息不进对话历史 → Claude可能不读取复盘内容
→ 复盘内容无法被利用
```

### 解决方案：主动提示读取

```python
# hermes/core/scheduler.py

def inject_phase_start_prompt(self, task_id, phase):
    """注入阶段开始prompt，提示读取复盘"""

    # 检查是否有上一阶段复盘
    review_path = f"tasks/{task_id}/reviews/{prev_phase}_review.json"
    if os.path.exists(review_path):
        prompt = f"""
上一阶段({prev_phase})复盘已完成。
复盘路径：{review_path}
建议参考复盘内容优化本阶段执行。

如需参考，请主动Read该文件。
"""
        # 注入到下一阶段prompt开头
```

### 触发时机

```
阶段N开始 → Hermes检查阶段N-1复盘是否存在
→ 存在则注入提示prompt
→ Claude决定是否Read（自主控制上下文）
```

---

## 补充设计：复盘知识库索引

### 知识库目录结构

```
knowledge/
├── reviews_index.json         # 全局复盘索引
├── lessons_learned/
│   ├── lesson_001.json        # 经验提炼
│   ├── lesson_002.json
│   └── ...
└── patterns/
    ├── pattern_001.json       # 设计模式
    └── ...
```

### reviews_index.json格式

```json
{
  "reviews": [
    {
      "task_id": "task_001",
      "phase": "概要设计",
      "review_path": "tasks/task_001/reviews/概要设计_review.json",
      "quality_score": 8,
      "lessons": ["状态机设计应先画图再编码"],
      "timestamp": "2026-04-19T10:36:00Z"
    }
  ],
  "total_lessons": 12,
  "total_patterns": 5
}
```

### 知识提取流程

```
任务完成 → Haiku任务复盘 → 提取lessons_learned
→ 存入knowledge/lessons_learned/lesson_xxx.json
→ 更新knowledge/reviews_index.json

下次任务：
→ 拆分Agent读取reviews_index → 参考历史经验
→ 避免"重复踩坑"
```

---

## 补充设计：复盘内容检索

### 按任务ID检索

```python
# hermes/core/knowledge_retrieval.py（扩展）

def get_reviews_by_task(self, task_id):
    """获取任务所有复盘"""

    reviews = []
    review_dir = f"tasks/{task_id}/reviews/"
    if os.path.exists(review_dir):
        for file in os.listdir(review_dir):
            if file.endswith('_review.json'):
                reviews.append(json.load(open(f"{review_dir}/{file}")))
    return reviews
```

### 按经验类型检索

```python
def get_lessons_by_type(self, lesson_type):
    """按类型检索经验"""

    # lesson_type: design, testing, implementation, coordination
    lessons = []
    index = json.load(open("knowledge/reviews_index.json"))
    for review in index['reviews']:
        for lesson in review['lessons']:
            if lesson['type'] == lesson_type:
                lessons.append(lesson)
    return lessons
```

---

## 待实现模块（更新）

| 模块 | 文件 | 说明 |
|------|------|------|
| NodeSummarizer | `hermes/core/node_summarizer.py` | 异步复盘Agent |
| HaikuClient | `hermes/core/haiku_client.py` | Haiku API客户端 |
| ReviewNotifier | `hermes/core/review_notifier.py` | 复盘提示注入 |
| KnowledgeIndexer | `hermes/core/knowledge_indexer.py` | 知识库索引管理 |
| LessonExtractor | `hermes/core/lesson_extractor.py` | 经验提炼提取 |