# ClaudeFlow 操作手册

> 最后更新日期 2026-04-25

本文档面向 ClaudeFlow 的使用者，提供从环境搭建到日常操作的完整指南。所有命令和路径均从项目代码中确认，可直接复制执行。

---

## 目录

1. [前置条件](#1-前置条件)
2. [开发环境启动](#2-开发环境启动)
3. [Runtime Console 使用](#3-runtime-console-使用)
4. [CLI 使用](#4-cli-使用)
5. [Task Graph 编写指南](#5-task-graph-编写指南)
6. [部署与发布](#6-部署与发布)

---

## 1. 前置条件

### 1.1 Python 环境

- **Python 版本**: >= 3.10（`pyproject.toml` 中 `requires-python = ">=3.10"`）
- **包管理**: 推荐使用 `pip` 或 `uv`
- **Python 核心依赖**:
  - `fastapi >= 0.100.0`
  - `uvicorn[standard] >= 0.20.0`
  - `pydantic >= 2.0.0`
  - `sentence-transformers >= 2.2.0`
  - `numpy >= 1.20.0`

### 1.2 Node.js 环境

- **Node 版本**: 建议 >= 18（项目使用 Vite 8、Vue 3.5、TypeScript 6）
- **包管理**: `npm`（项目包含 `package-lock.json`）

### 1.3 Java 环境（可选，仅旧任务流页面需要）

- **JDK 版本**: 1.8（`pom.xml` 中 `java.version = 1.8`）
- **框架**: Spring Boot 2.6.15
- **构建工具**: Maven

### 1.4 外部依赖

- **Claude Code CLI**: Runtime 的 CLI 驱动器通过 `claude` 命令启动和干预会话，需确保 `claude` 命令在 PATH 中可用
- **Git**: Runtime worker 使用 `git worktree` 创建独立工作目录

---

## 2. 开发环境启动

ClaudeFlow 包含三个独立服务，根据使用场景按需启动：

| 服务 | 端口 | 用途 | 是否必需 |
|------|------|------|----------|
| Python Runtime | 8000 | Runtime API、Session 管理、CLI 驱动 | 必需 |
| 前端 Console | 5173 | Web 控制台 | 必需 |
| Java 后端 | 21000 | 旧任务流页面（Task Flow） | 可选 |

### 2.1 安装 Python 依赖

```bash
# 在项目根目录执行
cd /path/to/claudeflow

# 方式一：使用 pip 安装（开发模式）
pip install -e ".[dev]"

# 方式二：使用 uv 安装
uv pip install -e ".[dev]"
```

`[dev]` 会额外安装 `pytest >= 7.0` 和 `pytest-cov >= 4.0`。

### 2.2 启动 Python Runtime 服务

Runtime API 服务由 FastAPI + uvicorn 提供，入口文件为 `src/claudeflow/runtime/api.py`。

```bash
# 方式一：直接使用 uvicorn 启动（推荐）
uvicorn claudeflow.runtime.api:app --host 0.0.0.0 --port 8000 --reload

# 方式二：直接运行入口文件
python -m claudeflow.runtime.api
```

启动后可访问以下地址验证：

- 健康检查: `http://localhost:8000/health`
- API 文档: `http://localhost:8000/docs`（FastAPI 自动生成的 Swagger UI）

### 2.3 安装前端依赖并启动 Console

```bash
cd /path/to/claudeflow/console

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

启动后访问 `http://localhost:5173`。

### 2.4 Vite 代理配置说明

前端 `console/vite.config.ts` 中配置了三个代理规则：

| 代理路径 | 目标服务 | 说明 |
|----------|----------|------|
| `/api` | `http://localhost:21000` | 代理到 Java 后端，供旧任务流页面使用 |
| `/ws` | `http://localhost:21000` | WebSocket 代理到 Java 后端 |
| `/runtime-api` | `http://localhost:8000` | 代理到 Python Runtime，路径重写 `/runtime-api` -> `/api` |

这意味着前端代码中：
- `/runtime-api/runtime/status` 实际请求 `http://localhost:8000/api/runtime/status`
- `/runtime-api/session/xxx/events-list` 实际请求 `http://localhost:8000/api/session/xxx/events-list`
- `/api/tasks` 实际请求 `http://localhost:21000/api/tasks`

### 2.5 启动 Java 后端（可选）

仅在使用旧任务流页面（Task Flow）时需要启动 Java 后端。

```bash
cd /path/to/claudeflow

# 使用 Maven 启动
./mvnw spring-boot:run

# 或使用本地 Maven
mvn spring-boot:run
```

Java 后端启动在端口 21000，使用 SQLite 数据库（`~/.claudeflow/console.db`）。

### 2.6 联调方式

**最小联调（推荐，只需 Runtime Console）**：

```bash
# 终端 1：启动 Python Runtime
uvicorn claudeflow.runtime.api:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：启动前端
cd console && npm run dev
```

访问 `http://localhost:5173/runtime`，进入 Runtime Console。该页面所有数据通过 `/runtime-api` 代理到 Python Runtime 服务。

**完整联调（包含旧任务流页面）**：

```bash
# 终端 1：启动 Java 后端
./mvnw spring-boot:run

# 终端 2：启动 Python Runtime
uvicorn claudeflow.runtime.api:app --host 0.0.0.0 --port 8000 --reload

# 终端 3：启动前端
cd console && npm run dev
```

- `http://localhost:5173/` -- Dashboard（旧任务流 + Runtime 入口）
- `http://localhost:5173/runtime` -- Runtime Console
- `http://localhost:5173/task/:id` -- TaskDetail（旧任务详情 + Runtime 跳转入口）

---

## 3. Runtime Console 使用

### 3.1 页面入口

Runtime Console 的路由路径为 `/runtime`，可通过以下方式访问：

- 直接访问 `http://localhost:5173/runtime`
- 从 Dashboard 首页（`/`）点击"进入 Runtime Console"卡片
- 从 TaskDetail 页面（`/task/:id`）顶部点击"打开 Runtime Console"链接

### 3.2 功能概览

Runtime Console 提供以下功能区域：

**运行时总览（Runtime Overview）**：
- Active Agents 数量
- Queued / Completed / Failed 任务计数
- Intervention Required 标记
- Running Tasks ID 列表
- Repo 路径显示

**Session 列表操作**：
- 解释任务（Explain）-- 查询单任务为何可运行或被阻塞
- 查看事件（View Events）-- 查看 session 的 parsed 事件列表
- 发送干预（Intervene）-- 向运行中的 session 注入干预 prompt
- 标记完成（Complete）-- 将任务标记为 completed
- 标记失败（Fail）-- 将任务标记为 failed

**Plan 面板**：
- 展示 runnable / blocked / running 三类任务
- 每个任务附带 priority 和 reason_code

**Explain 面板**：
- 输入 task_id，查询该任务的状态和阻塞原因
- 展示 state、priority、reason_code、reason、dependencies

**Dispatch 面板**：
- 执行一次调度，自动启动可运行任务
- 展示 started / skipped / blocked 结果

### 3.3 Sample 模式 vs Live 模式

Runtime Console 支持两种数据模式：

**Sample 模式**：
- 页面默认加载内置示例数据
- 数据来源于 `console/src/services/runtimeApi.ts` 中定义的 `runtimePlanSample`、`runtimeExplainSample`、`runtimeDispatchSample` 等常量
- 不需要后端服务即可查看页面结构和交互
- 点击"加载示例数据"按钮可随时恢复 sample 数据

**Live 模式**：
- 点击"读取 Live Plan"、"读取 Live 总览"、"读取 Live Explain"、"执行 Live Dispatch"等按钮，从 Python Runtime API 获取真实数据
- 数据来源标记（source badge）会从 `SAMPLE` 变为 `LIVE`
- 需要 Python Runtime 服务在 8000 端口运行

### 3.4 自动刷新

Runtime Console 支持自动刷新功能：

- 勾选"自动刷新"复选框启用
- 轮询间隔可选 3s / 5s / 10s / 15s
- 开启后自动刷新 live plan、explain 和 running session 的事件
- 页面显示"最近刷新"时间戳

---

## 4. CLI 使用

### 4.1 安装 CLI 工具

安装 Python 包后，`claudeflow` 命令自动注册（entry point 定义在 `pyproject.toml` 中 `claudeflow = "claudeflow.cli:main"`）。

```bash
pip install -e .
```

### 4.2 环境变量

CLI 支持两个环境变量：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CLAUDFLOW_TASKS_DIR` | `./tasks` | 任务存储目录 |
| `CLAUDFLOW_REPO_DIR` | 当前工作目录 | 仓库根目录（Runtime worktree 在此目录下创建） |

### 4.3 命令总览

```
claudeflow <command> [options]
```

| 命令 | 说明 |
|------|------|
| `task create` | 创建任务 |
| `task list` | 列出任务 |
| `task show` | 查看任务详情 |
| `status` | 查看系统状态 |
| `runtime init` | 初始化 Runtime 目录 |
| `runtime status` | 查看 Runtime 总览 |
| `runtime plan` | 查看调度计划 |
| `runtime show` | 查看单任务会话详情 |
| `runtime explain` | 解释单任务状态 |
| `runtime start` | 启动 Runtime Worker |
| `runtime complete` | 完成 Runtime Worker |
| `runtime fail` | 标记 Runtime Worker 失败 |
| `runtime dispatch` | 自动启动可运行任务 |

### 4.4 Task 命令

#### 创建任务

```bash
claudeflow task create --name "实现用户认证" --domain "auth" --priority "高" --description "实现JWT认证模块"
```

参数说明：

| 参数 | 必需 | 说明 |
|------|------|------|
| `--name` | 是 | 任务名称 |
| `--domain` | 是 | 业务领域 |
| `--priority` | 否 | 优先级，默认"中" |
| `--description` | 否 | 任务描述 |

#### 列出任务

```bash
# 列出所有任务
claudeflow task list

# 按状态过滤
claudeflow task list --status running

# 限制数量
claudeflow task list --limit 10
```

#### 查看任务详情

```bash
claudeflow task show --id <task_id>
```

### 4.5 Status 命令

```bash
# 查看系统总览
claudeflow status --all

# 查看单个任务状态
claudeflow status --task <task_id>
```

### 4.6 Runtime 命令

#### 初始化 Runtime 目录

```bash
claudeflow runtime init
```

在仓库目录下创建 `.claudeflow/` 目录结构：

```
.claudeflow/
├── sessions/          # 会话索引
├── checkpoints/       # 检查点
├── locks/             # 写锁
├── transcript-mirror/ # 事件转录
├── handoff/           # 交接
├── runtime-status.json # 运行时状态
└── task-graph.json    # 任务图
```

#### 查看 Runtime 状态

```bash
claudeflow runtime status
```

输出示例：

```
ClaudeFlow Runtime 状态:
  Repo: /path/to/repo
  Active Agents: 2
  Queued Tasks: 3
  Completed Tasks: 5
  Failed Tasks: 1
  Intervention Required: True
  Running Tasks: impl_auth, impl_payment
  Session Indexes: 8
```

#### 查看调度计划

```bash
# 查看当前调度计划
claudeflow runtime plan

# 从 task graph 文件加载后查看
claudeflow runtime plan --task-graph-file examples/task-graph.sample.json

# JSON 格式输出
claudeflow runtime plan --task-graph-file examples/task-graph.sample.json --json
```

输出包含三类任务：runnable（可运行）、blocked（阻塞）、running（运行中）。

#### 查看单任务详情

```bash
claudeflow runtime show --task-id impl_auth_controller
```

输出包含：Session ID、状态、Worktree 路径、Owner Role、Task Type、Write Paths、Protocol Refs、Design Refs、Summary。

#### 解释单任务

```bash
claudeflow runtime explain --task-id impl_auth_tests

# 从 task graph 加载后解释
claudeflow runtime explain --task-id impl_auth_tests --task-graph-file examples/task-graph.sample.json

# JSON 格式输出
claudeflow runtime explain --task-id impl_auth_tests --task-graph-file examples/task-graph.sample.json --json
```

输出包含：State（runnable/blocked/completed/failed）、Priority、Reason Code、Reason、Dependencies。

Reason Code 取值：

| Code | 含义 |
|------|------|
| `ready` | 依赖已满足，可运行 |
| `missing_dependency` | 依赖任务在 task graph 中不存在 |
| `upstream_failed` | 上游任务失败，按策略跳过 |
| `waiting_dependency` | 等待上游依赖完成 |
| `waiting_slot` | 等待可用并发槽位 |
| `write_lock_conflict` | 写入路径与其他任务冲突 |
| `session_running` | 已有运行中的会话 |
| `session_completed` | 会话已完成 |
| `session_failed` | 会话已失败 |

#### 启动 Runtime Worker

```bash
# 方式一：从 task graph 文件加载并启动
claudeflow runtime start \
  --task-id impl_auth_controller \
  --task-graph-file examples/task-graph.sample.json \
  --base-branch HEAD

# 方式二：直接指定参数启动
claudeflow runtime start \
  --task-id my_task \
  --prompt "实现用户认证模块" \
  --owner-role worker-agent \
  --task-type ImplementTask \
  --base-branch HEAD \
  --write-path src/controllers/AuthController.java \
  --read-path src/auth/** \
  --protocol-ref auth_api@v2 \
  --design-ref architecture@v2
```

参数说明：

| 参数 | 必需 | 说明 |
|------|------|------|
| `--task-id` | 是 | 任务唯一标识 |
| `--task-graph-file` | 否 | Task graph JSON 文件路径 |
| `--prompt` | 条件必需 | 任务描述（未指定 `--task-graph-file` 时必需） |
| `--owner-role` | 否 | 执行角色，默认 `worker-agent` |
| `--task-type` | 否 | 任务类型，默认 `ImplementTask` |
| `--base-branch` | 否 | 基线分支，默认 `HEAD` |
| `--write-path` | 否 | 写入路径（可多次指定） |
| `--read-path` | 否 | 读取路径（可多次指定） |
| `--protocol-ref` | 否 | 协议引用（可多次指定） |
| `--design-ref` | 否 | 设计引用（可多次指定） |

启动后，Runtime 会：
1. 检查 write_paths 是否与其他任务冲突
2. 创建 `git worktree`（路径为 `.worktrees/<task_id>`）
3. 在 worktree 中启动 Claude Code CLI 进程
4. 记录 session 索引到 `.claudeflow/sessions/<task_id>.json`

#### 完成 Runtime Worker

```bash
claudeflow runtime complete \
  --task-id impl_auth_controller \
  --summary "Auth controller 已完成并通过测试" \
  --changed-file src/controllers/AuthController.java \
  --test-status passed \
  --test-count 12
```

参数说明：

| 参数 | 必需 | 说明 |
|------|------|------|
| `--task-id` | 是 | 任务标识 |
| `--summary` | 否 | 完成摘要 |
| `--changed-file` | 否 | 变更文件（可多次指定） |
| `--test-status` | 否 | 测试状态 |
| `--test-count` | 否 | 测试数量 |

完成后会创建 checkpoint，释放写锁，并输出新可运行任务列表。

#### 标记 Runtime Worker 失败

```bash
claudeflow runtime fail \
  --task-id impl_auth_controller \
  --reason "上游接口变更，当前实现无法通过测试"
```

#### 自动调度（Dispatch）

```bash
# 基本调度
claudeflow runtime dispatch --task-graph-file examples/task-graph.sample.json

# 限制并发数
claudeflow runtime dispatch \
  --task-graph-file examples/task-graph.sample.json \
  --max-concurrent 2

# 限制本次启动数量
claudeflow runtime dispatch \
  --task-graph-file examples/task-graph.sample.json \
  --limit 3

# JSON 格式输出
claudeflow runtime dispatch \
  --task-graph-file examples/task-graph.sample.json \
  --json
```

参数说明：

| 参数 | 必需 | 说明 |
|------|------|------|
| `--task-graph-file` | 是 | Task graph JSON 文件路径 |
| `--base-branch` | 否 | 基线分支，默认 `HEAD` |
| `--limit` | 否 | 本次最多启动任务数 |
| `--max-concurrent` | 否 | 最大并发槽位 |
| `--json` | 否 | JSON 格式输出 |

调度会按 priority 排序启动可运行任务，跳过写锁冲突的任务，并报告阻塞原因。

---

## 5. Task Graph 编写指南

### 5.1 Schema 结构

Task graph 是一个 JSON 文件，定义一组任务及其依赖关系。Schema 文件位于 `examples/task-graph.schema.json`。

最小结构：

```json
{
  "tasks": [
    {
      "task_id": "唯一标识",
      "prompt": "任务描述"
    }
  ]
}
```

完整字段：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `task_id` | string | 是 | 任务唯一标识 |
| `prompt` | string | 是 | 任务描述，会传给 Claude Code CLI |
| `owner_role` | string | 否 | 执行角色，如 `worker-agent`、`backend-agent`、`qa-agent` |
| `task_type` | string | 否 | 任务类型，如 `ImplementTask` |
| `priority` | string/integer | 否 | 优先级，支持 `p0`/`urgent`/`critical`/`high`/`medium`/`low` 等或数字 |
| `depends_on` | string[] | 否 | 依赖的 task_id 列表 |
| `read_paths` | string[] | 否 | 允许读取的路径（支持 glob） |
| `write_paths` | string[] | 否 | 允许写入的路径（用于写锁检测） |
| `shared_files` | string[] | 否 | 共享文件路径 |
| `protocol_refs` | string[] | 否 | 协议文档引用 |
| `design_refs` | string[] | 否 | 设计文档引用 |

### 5.2 示例文件

项目提供了示例 task graph 文件（`examples/task-graph.sample.json`），展示了一个包含依赖关系的两任务场景：

- `impl_auth_controller`：实现认证控制器（high 优先级，无依赖）
- `impl_auth_tests`：编写认证测试（medium 优先级，依赖 `impl_auth_controller`）

### 5.3 优先级排序规则

Runtime Manager 支持以下优先级值（数值越小优先级越高）：

| 优先级 | 数值 |
|--------|------|
| `p0` / `urgent` / `critical` / `最高` | 0 |
| `high` / `p1` / `高` | 1 |
| `medium` / `normal` / `p2` / `中` | 2 |
| `low` / `p3` / `低` | 3 |
| 数字字符串 | 对应数值 |
| 其他 | 2（中等） |

---

## 6. 部署与发布

### 6.1 Python 包构建

```bash
cd /path/to/claudeflow

# 构建 wheel 和 sdist
pip install build
python -m build
```

构建产物在 `dist/` 目录下。项目使用 setuptools 构建后端（`pyproject.toml` 中 `build-backend = "setuptools.build_meta"`）。

### 6.2 pip 安装

```bash
# 从本地源码安装
pip install /path/to/claudeflow

# 从构建产物安装
pip install dist/claudeflow-0.1.0-py3-none-any.whl

# 开发模式安装（可编辑）
pip install -e /path/to/claudeflow
```

### 6.3 前端 Console 构建

```bash
cd /path/to/claudeflow/console

# 生产构建
npm run build
```

构建产物在 `console/dist/` 目录下，为静态 HTML/JS/CSS 文件。

### 6.4 Java 后端构建（可选）

```bash
cd /path/to/claudeflow

# 打包
./mvnw package -DskipTests

# 或使用本地 Maven
mvn package -DskipTests
```

构建产物为 `target/claudeflow-console-2.4.0.jar`。

### 6.5 生产环境部署

#### 方案一：仅 Runtime Console（推荐最小部署）

```
[Python Runtime :8000]  <--  [Nginx/反向代理 :80]  -->  [静态文件: console/dist/]
```

1. 构建前端静态文件：`cd console && npm run build`
2. 将 `console/dist/` 部署到 Nginx 或其他静态文件服务器
3. 启动 Python Runtime 服务：
   ```bash
   uvicorn claudeflow.runtime.api:app --host 0.0.0.0 --port 8000
   ```
4. 配置 Nginx 代理规则：
   - `/` --> 静态文件目录
   - `/runtime-api/` --> `http://localhost:8000/api/`（路径重写）
   - `/health` --> `http://localhost:8000/health`

#### 方案二：完整部署（含旧任务流页面）

```
[Java Backend :21000]  <--  [Nginx/反向代理 :80]  -->  [静态文件: console/dist/]
[Python Runtime :8000]  <--/
```

除方案一的配置外，还需：
1. 启动 Java 后端：
   ```bash
   java -jar target/claudeflow-console-2.4.0.jar
   ```
2. Nginx 额外代理规则：
   - `/api/` --> `http://localhost:21000/api/`
   - `/ws` --> `http://localhost:21000/ws`（WebSocket）

#### 生产环境注意事项

- **CORS 配置**: Python Runtime API 的 CORS 允许源定义在 `src/claudeflow/runtime/api.py` 中，生产环境需修改为实际域名
- **CORS 配置 (Java)**: Java 后端的 CORS 配置在 `src/main/resources/application.yml` 中
- **Session 持久化**: 当前 Python Runtime 的 session 数据存储在文件系统（`.claudeflow/sessions/`），重启不丢失
- **数据库**: Java 后端使用 SQLite（`~/.claudeflow/console.db`），适合单机部署
- **Claude Code CLI**: 生产服务器上需要安装 `claude` CLI 并确保 PATH 可用
- **Git Worktree**: Runtime worker 会在仓库目录下创建 `.worktrees/` 子目录，确保磁盘空间充足
- **进程管理**: 建议使用 systemd 或 supervisord 管理 Python Runtime 和 Java 后端进程

---

## 附录：Runtime API 端点速查

### Session 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/session/start` | 启动新 Session |
| GET | `/api/session/{session_id}/status` | 查询 Session 状态 |
| GET | `/api/session/{session_id}/events` | SSE 事件流 |
| GET | `/api/session/{session_id}/events-list` | 事件列表（JSON） |
| POST | `/api/session/{session_id}/intervene` | 发送干预 |
| POST | `/api/session/{session_id}/cancel` | 取消 Session |

### Runtime 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/runtime/status` | Runtime 总览状态 |
| GET | `/api/runtime/sessions` | 列出所有 Session |
| GET | `/api/runtime/plan` | 调度计划 |
| GET | `/api/runtime/explain/{task_id}` | 解释单任务 |
| POST | `/api/runtime/dispatch` | 执行调度 |
| POST | `/api/runtime/task/{task_id}/complete` | 完成任务 |
| POST | `/api/runtime/task/{task_id}/fail` | 标记失败 |

### Health

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
