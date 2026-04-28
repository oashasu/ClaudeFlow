# OneAPI 部署指南

> 东京云服务器 NewAPI (OneAPI增强版) 部署记录

## 服务器信息

| 项目 | 值 |
|------|------|
| 公网 IP | `43.130.249.159` |
| SSH 端口 | 22 (已开放) |
| NewAPI 端口 | 3000 (需安全组开放) |

## 已部署组件

| 组件 | 状态 | 端口 | 说明 |
|------|------|------|------|
| Docker | ✅ 已安装 | - | 版本 29.1.3 |
| NewAPI 容器 | ✅ 运行中 | 3000 | `calciumion/new-api:latest` |
| 管理员账号 | ✅ 已创建 | - | 见下方 |
| API Token | ✅ 已生成 | - | 见下方 |
| 腾讯云安全组 | ✅ 已配置 | 3000 | 端口已开放 |
| 阿里百炼渠道 | ✅ 已配置 | - | Coding Plan套餐 |
| 模型价格 | ✅ 已配置 | - | glm-5, qwen3.6-plus 价格设为0 |
| 用户额度 | ✅ 已配置 | - | admin用户额度充足 |
| 连通性测试 | ✅ 通过 | - | glm-5, qwen3.6-plus 调用成功 |

## 登录信息

**Web UI 地址**（需先开放安全组端口 3000）：
```
http://43.130.249.159:3000
```

**管理员账号**：
```
用户名: admin
密码: ClaudeFlowAdmin2026
```

**API Token（供 ClaudeFlow 调用）**：

| 用户 | 令牌名称 | API Key |
|------|----------|---------|
| admin | ClaudeFlow-Main | `sk-DewQyKUh68KnuIVTNORO7R682YNjO9T6C8KqyH7tZbhS2MvL` |
| 赵宁 | 赵宁 | `sk-GLplsnZSnxIPytflPeZkUajMiG3KLI3AkDh248SBt9PSKwsR` |
| 宋少辉 | 宋少辉 | `sk-SFXoHRMSU2nImuoUFYobZyxBQOepjz03gxRSoI5nmpTxIj8C` |
| 王绯绯 | 王绯绯 | `sk-wsATd5IxZb8tsFej4I0JOl5sPTYBxsCfx9KLWbx8Xf4MRoQG` |
| 朱东志 | 朱东志 | `sk-RnzHgnsSVNofPgMsDkGyq7nCCddxaFVGqqYMSbXCFLsSiYR4` |
| 史志友 | 史志友 | `sk-5m04pVbj4LnPcAx5DYAN8ssiJwx3kPVzrB8itqOfDYGNuRHd` |

## 腾讯云安全组配置

需要在腾讯云控制台添加入站规则：

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 3000 | 0.0.0.0/0 或指定IP | NewAPI Web UI 和 API |

**配置步骤**：
1. 登录腾讯云控制台
2. 进入「云服务器 CVM」→ 选择实例
3. 点击「安全组」→「编辑规则」
4. 添加入站规则：TCP 端口 3000

## 阿里百炼 Coding Plan 渠道

### 渠道配置信息

| 配置项 | 值 |
|--------|-----|
| 渠道名称 | 阿里百炼 |
| 渠道类型 | 阿里云百炼 |
| Base URL | `https://coding.dashscope.aliyuncs.com/apps/anthropic` |
| API Key | 用户已配置（存储在服务器数据库） |
| 支持模型 | `glm-5`, `qwen3.6-plus` 及其他 Coding Plan 模型 |
| 状态 | ✅ 启用并连通 |

### Coding Plan 支持的模型列表

| 品牌 | 模型 | 能力 |
|------|------|------|
| 千问 | qwen3.6-plus | 文本生成、深度思考、视觉理解 |
| 千问 | qwen3.5-plus | 文本生成、深度思考、视觉理解 |
| 千问 | qwen3-max-2026-01-23 | 文本生成、深度思考 |
| 千问 | qwen3-coder-next | 文本生成 |
| 千问 | qwen3-coder-plus | 文本生成 |
| 智谱 | glm-5 | 文本生成、深度思考 |
| 智谱 | glm-4.7 | 文本生成、深度思考 |
| Kimi | kimi-k2.5 | 文本生成、深度思考、视觉理解 |
| MiniMax | MiniMax-M2.5 | 文本生成、深度思考 |

### 方式一：Web UI 配置（推荐，更安全）

#### 第一步：登录
1. 浏览器访问 `http://43.130.249.159:3000`
2. 输入账号密码：
   - 用户名：`admin`
   - 密码：`ClaudeFlowAdmin2026`
3. 点击「登录」

#### 第二步：进入渠道管理
登录后，左侧菜单栏找到：
```
渠道管理 → 点击进入
```
位置：菜单第二项（图标像管道/链接）

#### 第三步：编辑渠道
在渠道列表中找到「阿里百炼」渠道：
1. 点击该渠道右侧的「编辑」按钮（铅笔图标）
2. 进入编辑页面

#### 第四步：填入 API Key
编辑页面关键字段：

| 字段 | 填写内容 |
|------|----------|
| **名称** | 保持「阿里百炼」（可不改） |
| **类型** | 保持「阿里云百炼」 |
| **Base URL** | 保持默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| **密钥** | ⬇️ **填入你的真实 API Key** |
| **模型** | 已配置，保持不变 |

密钥字段就是 API Key 输入框，把你的 Key 粘贴进去。

#### 第五步：测试连通性
填入 Key 后：
1. 点击页面底部「测试」按钮
2. 等待测试结果：
   - ✅ 绿色提示 = 配置成功
   - ❌ 红色提示 = Key 无效或网络问题

#### 第六步：保存
测试成功后：
1. 点击「提交」或「保存」按钮
2. 渠道状态变为「启用」

#### 配置完成验证
回到渠道列表，确认：
- 阿里百炼渠道状态显示为「启用」（绿色）
- 可以点击「测试」再次验证

### 方式二：通过我配置

如果你信任当前对话的安全性，可以：
1. 把 API Key 告诉我
2. 我通过 SSH 直接更新数据库
3. **安全建议**：配置完成后，删除包含 API Key 的那条消息

**安全保障措施**：
- API Key 存储在服务器 SQLite 数据库中
- 不会写入任何持久化文档文件
- 配置完成后立即重启容器使生效
- 你可以随时在 Web UI 中更换 Key

## 并发限制动态调整

NewAPI 支持在「系统设置」中动态调整：

| 参数 | 作用 | 默认值 |
|------|------|--------|
| 渠道并发上限 | 单渠道最大并发请求 | 可动态调整 |
| 排队超时 | 请求排队等待时间 | 30秒 |
| 自动重试 | 失败后自动重试次数 | 3次 |

Web UI →「系统设置」→「速率限制」可实时修改，无需重启。

## ClaudeFlow 调用配置

配置 ClaudeFlow 使用 NewAPI 作为网关：

```python
# Runtime 层配置
- max_concurrent=6  # 比 OneAPI 设置低 1，留冗余
- 任务启动间隔 200ms
```

**调用地址**：
```
Base URL: http://43.130.249.159:3000/v1
API Key: sk-DewQyKUh68KnuIVTNORO7R682YNjO9T6C8KqyH7tZbhS2MvL
```

## 常用运维命令

```bash
# SSH 连接
ssh root@43.130.249.159

# 查看容器状态
docker ps | grep one-api

# 查看日志
docker logs one-api --tail 100

# 重启容器
docker restart one-api

# 查看数据库
sqlite3 /opt/one-api/one-api.db "SELECT id, name, models FROM channels;"
```

## 配置完成状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. 腾讯云安全组开放端口 3000 | ✅ 完成 | 端口已开放，外部可访问 |
| 2. 配置阿里百炼真实 API Key | ✅ 完成 | 用户已通过 Web UI 配置 |
| 3. 测试渠道连通性 | ✅ 完成 | glm-5, qwen3.6-plus 调用成功 |
| 4. ClaudeFlow Runtime 集成调用 | ⏳ 待配置 | 需修改 Runtime 配置指向 OneAPI |

## ClaudeFlow Runtime 集成（下一步）

将 ClaudeFlow 的模型调用指向 OneAPI 网关：

```python
# Runtime 配置修改
base_url = "http://43.130.249.159:3000/v1"
api_key = "sk-DewQyKUh68KnuIVTNORO7R682YNjO9T6C8KqyH7tZbhS2MvL"
default_model = "glm-5"  # 或 "qwen3.6-plus"
max_concurrent = 6  # 留1个冗余，避免触达并发红线
```