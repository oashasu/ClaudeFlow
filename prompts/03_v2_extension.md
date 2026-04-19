# 阶段3：V2扩展

## 任务目标

在V1基础上添加通信层、Agent提炼、前置拆分等扩展功能。

## 前置条件

- V1验收通过
- V2设计文档已阅读

## V2新增模块

| 模块 | 职责 |
|------|------|
| websocket_client | WebSocket通信 |
| session_parser | 解析.jsonl |
| thinking_filter | 死循环检测 |
| phase_reviewer | 阶段复盘 |
| task_reviewer | 任务复盘 |
| progress_reporter | 进度推送 |
| alert_handler | 告警处理 |

## V2修改模块

| 模块 | 修改内容 |
|------|----------|
| checkpoint | 借鉴LangGraph接口 |
| scheduler | 添加Session生命周期 |

## 执行步骤

### Step 1：阅读V2设计文档

```bash
# 阅读所有V2设计文档
/Users/claw/sandbox/personal/claudflow/docs/01_通信层设计.md
/Users/claw/sandbox/personal/claudflow/docs/02_Agent提炼机制设计.md
/Users/claw/sandbox/personal/claudflow/docs/03_前置拆分流程设计.md
/Users/claw/sandbox/personal/claudflow/docs/04_强制checkpoint机制设计.md
/Users/claw/sandbox/personal/claudflow/docs/05_子Agent异步总结设计.md
/Users/claw/sandbox/personal/claudflow/docs/06_Claude_Code输出格式规范.md
```

### Step 2：创建V2分支

```bash
cd /Users/claw/sandbox/personal/claudflow
git checkout -b v2
```

### Step 3：按优先级开发V2模块

优先级顺序（参考07_V2设计问题清单.md）：
1. session_parser（基础）
2. thinking_filter（基础）
3. websocket_client（通信）
4. progress_reporter（通信）
5. alert_handler（通信）
6. phase_reviewer（复盘）
7. task_reviewer（复盘）

### Step 4：每个模块继续TDD流程

```bash
# 创建测试
touch tests/unit/test_<module>.py

# 写测试 -> 写实现 -> 验证覆盖率
pytest tests/ -v --cov
```

### Step 5：修改checkpoint模块

借鉴LangGraph接口设计：
```python
class CheckpointSaver:
    def get_tuple(self, config): ...
    def put(self, config, checkpoint): ...
    def put_writes(self, config, writes): ...
```

## V2验收标准

- 全部测试通过（含V1+V2）
- 覆盖率 >= 80%
- WebSocket通信可用
- Agent提炼可用

## 参考文档

- `/Users/claw/sandbox/personal/claudflow/docs/*.md` - 所有V2设计文档
- LangGraph Checkpoint接口（参考）

## 注意事项

- 基于V1代码扩展，不重写
- 继续TDD流程
- 功能留白，逐步完善