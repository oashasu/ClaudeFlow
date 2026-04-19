# 阶段1：V1开发（核心功能 + TDD验证）

## 任务目标

实现ClaudeFlow V1最小版本，验证核心功能和TDD流程可行性。

## 前置条件

- GitHub仓库已创建
- 设计文档已阅读：`/Users/claw/sandbox/personal/claudflow/docs/INDEX.md`

## V1模块清单

| 模块 | 职责 | 优先级 |
|------|------|--------|
| state_machine | 七状态模型 | P0 |
| task_manager | 任务CRUD | P0 |
| scheduler | 流程调度 | P0 |
| cli_interface | CLI命令 | P0 |
| checkpoint | 状态快照 | P1 |
| employee_pool | 三层员工池 | P2 |
| knowledge_retrieval | 三层检索 | P2 |

## TDD流程要求

**严格执行**：
1. 先写测试（RED）
2. 运行测试 - 应该失败
3. 写最小实现（GREEN）
4. 运行测试 - 应该通过
5. 重构（IMPROVE）
6. 验证覆盖率 >= 80%

## 执行步骤

### Step 1：项目结构初始化

```bash
cd /Users/claw/sandbox/personal/claudflow
mkdir -p src/claudflow tests/unit tests/integration tests/e2e
touch src/claudflow/__init__.py
```

创建pyproject.toml：
```toml
[project]
name = "claudflow"
version = "0.1.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Step 2：按优先级开发模块

**P0模块（必须完成）**：
1. state_machine - 七状态模型
2. task_manager - 任务CRUD
3. scheduler - 流程调度
4. cli_interface - CLI命令

**P1模块（重要）**：
5. checkpoint - 状态快照

**P2模块（可选）**：
6. employee_pool - 三层员工池
7. knowledge_retrieval - 三层检索

### Step 3：每个模块的TDD流程

对于每个模块：
```bash
# 1. 创建测试文件
touch tests/unit/test_<module>.py

# 2. 写测试用例（先失败）
pytest tests/unit/test_<module>.py -v

# 3. 创建实现文件
touch src/claudflow/<module>.py

# 4. 写最小实现（让测试通过）
pytest tests/unit/test_<module>.py -v

# 5. 重构 + 验证覆盖率
pytest --cov=src/claudflow tests/
```

## V1验收标准

- 单元测试 >= 150个
- 集成测试 >= 30个
- E2E测试 >= 10个
- 测试覆盖率 >= 80%
- CLI可用（create/list/status命令）

## 参考文档

- `/Users/claw/sandbox/personal/claudflow/docs/INDEX.md` - V1设计
- `/Users/claw/sandbox/tasks/2026-04-18_Hermes系统设计/04_详细设计/` - V1详细设计（参考）

## 注意事项

- 不做WebSocket通信（V2）
- 不做Agent提炼（V2）
- 不做前置拆分（V2）
- 只实现核心CLI + 流程调度