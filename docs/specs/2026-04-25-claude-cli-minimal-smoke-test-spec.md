# Claude CLI 最小化测试规格

> 日期：2026-04-25
> 状态：active
> 优先级：P0
> 前置条件：本机已安装 Claude Code CLI（`/Users/claw/.local/bin/claude`）

## 目的

定义三层最小化测试，验证从 Claude CLI 本身到 ClaudeFlow runtime 调度链路的可用性。

## 第一层：Claude CLI 真机 Smoke Test

### 前置条件

- Claude Code CLI 已安装并可执行
- 认证已配置（`claude` 非首次运行）
- 网络可用

### 测试命令

```bash
claude -p "只回复 OK" --output-format stream-json --verbose
```

### 预期输出

输出应为 JSONL 格式（每行一个 JSON 对象），包含：

1. **system 事件**：首行包含 `session_id`
2. **assistant 事件**：包含 `"type": "assistant"`
3. **result 事件**：末行包含 `"type": "result"`

### 断言标准

| 检查项 | 通过条件 |
|--------|----------|
| CLI 启动 | 无报错，有 JSONL 输出 |
| session_id 存在 | 首行 JSON 包含非空 `session_id` |
| 响应内容 | 包含 assistant 事件 |
| 正常结束 | 末行为 result 事件，exit code = 0 |

### 失败判定

- `command not found` — CLI 未安装
- `Authentication required` — 认证未配置
- 非零 exit code — CLI 异常
- 无 JSONL 输出 — 参数错误或版本不兼容

### 版本确认

```bash
claude --version
# 预期：2.1.119 或更高
```

---

## 第二层：ClaudeFlow 单元测试

### 前置条件

- Python 3.10+
- 依赖已安装（`pip install -e ".[dev]"`）

### 测试命令

```bash
cd /Users/claw/sandbox/personal/claudeflow
PYTHONPATH=src pytest \
  tests/unit/test_cli_driver.py \
  tests/unit/test_runtime_manager.py \
  tests/unit/test_runtime_api.py \
  -v --tb=short
```

### 覆盖范围

| 测试文件 | 覆盖模块 | 验证内容 |
|----------|----------|----------|
| `test_cli_driver.py` | `runtime/cli_driver.py` | 命令构造（`-p`、`--output-format stream-json`、`--verbose`、`--session-id`、`--resume`）、session_id 提取、事件解析 |
| `test_runtime_manager.py` | `runtime/manager.py` | worktree 创建/清理、write_paths 逻辑锁、dispatch/complete/fail 状态流转、priority 排序、max_concurrent 槽位 |
| `test_runtime_api.py` | `runtime/api.py` | 全部 18 条路由注册、健康检查、session CRUD、runtime 操作的成功/404/错误场景 |

### 断言标准

- 全部通过，0 失败
- 不依赖联网，不调用真实 Claude CLI

### 已知排除

- `test_v3_integration.py` — 依赖 numpy（governance 模块），需单独环境
- `tests/unit/governance/` — 同上

---

## 第三层：ClaudeFlow Runtime 最小闭环

### 前置条件

- 第一层（CLI smoke test）已通过
- 第二层（单元测试）已通过
- 当前目录为 Git 仓库（runtime 需要 `.claudeflow/` 目录）

### 测试流程

```bash
cd /Users/claw/sandbox/personal/claudeflow

# 1. 初始化 runtime 目录
PYTHONPATH=src python3 -m claudeflow.cli runtime init

# 2. 查看调度计划（不应启动任何 CLI，只分析 task graph）
PYTHONPATH=src python3 -m claudeflow.cli runtime plan \
  --task-graph-file ./examples/task-graph.sample.json

# 3. 启动第一个 worker（会真正调用 Claude CLI）
PYTHONPATH=src python3 -m claudeflow.cli runtime start \
  --task-id impl_auth_controller \
  --prompt "回复 OK 即可，这是 smoke test" \
  --write-path src/controllers/AuthController.java \
  --task-graph-file ./examples/task-graph.sample.json

# 4. 查看状态
PYTHONPATH=src python3 -m claudeflow.cli runtime status
PYTHONPATH=src python3 -m claudeflow.cli runtime show --task-id impl_auth_controller

# 5. 标记完成（手工收尾，模拟闭环）
PYTHONPATH=src python3 -m claudeflow.cli runtime complete \
  --task-id impl_auth_controller \
  --summary "smoke test complete"

# 6. 验证下游任务变为 runnable
PYTHONPATH=src python3 -m claudeflow.cli runtime explain \
  --task-id impl_auth_tests \
  --task-graph-file ./examples/task-graph.sample.json
```

### 预期结果

| 步骤 | 预期 |
|------|------|
| `runtime init` | 创建 `.claudeflow/` 目录，无报错 |
| `runtime plan` | 输出 runnable/blocked/running 三类任务，`impl_auth_controller` 为 runnable |
| `runtime start` | 启动 CLI 进程，返回 session_id 和 worktree 路径 |
| `runtime status` | 显示 active_agents=1，running_tasks 包含 `impl_auth_controller` |
| `runtime show` | 显示 session_id、status=running |
| `runtime complete` | 标记完成，输出新变为 runnable 的任务（`impl_auth_tests`） |
| `runtime explain` | `impl_auth_tests` 状态为 runnable，reason_code 无阻塞 |

### 失败判定

| 步骤 | 可能失败原因 |
|------|-------------|
| `runtime init` | 非 Git 仓库 |
| `runtime start` | Claude CLI 不可用、认证过期、网络不通 |
| `runtime status` | `.claudeflow/` 目录损坏 |
| `runtime complete` | task_id 不存在 |

---

## 测试顺序

```
第一层（CLI smoke）→ 通过 → 第二层（单元测试）→ 通过 → 第三层（runtime 闭环）
       ↓ 失败                         ↓ 失败                    ↓ 失败
  修复 CLI 安装/认证              修复代码 bug              修复调度链路
```

**只有前一层通过后，才进入下一层。** 原因：

1. 第三层依赖真实 Claude CLI，第一层不通则第三层必败
2. 第二层不依赖 CLI，可以独立跑，但第三层的 bug 如果第二层就有，应先在第二层定位

## 现状评估

| 能力 | 状态 | 说明 |
|------|------|------|
| 最小单元测试 | ✅ 已有 | 不依赖联网，420 测试通过 |
| 最小真机 smoke test 入口 | ✅ 已有 | 一条 `claude -p` 命令即可 |
| 最小 runtime 闭环入口 | ✅ 已有 | README 中有完整命令示例 |
| 一键真机 e2e 脚本 | ❌ 缺失 | 需编写自动化脚本 |
| 自动断言真实 Claude 返回 | ❌ 缺失 | 依赖本机认证，不适合 CI |
| 稳定的 live e2e CI | ❌ 缺失 | 需稳定的认证和账户状态 |

## 后续建议

1. 将第一层 smoke test 集成为 `claude -p "只回复 OK" --output-format stream-json | python3 scripts/verify-cli-output.py`
2. 将第三层闭环写为 `scripts/runtime-smoke-test.sh`，自动执行 init→start→status→complete→explain 并断言每步输出
3. 这两个脚本不进入常规 pytest，作为手动验证入口（`scripts/` 目录）
