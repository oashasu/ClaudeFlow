# 阶段0：创建GitHub仓库

## 任务目标

在GitHub上创建ClaudeFlow项目仓库，配置基本结构。

## 前置条件

- 已安装gh CLI（`brew install gh`）
- 已登录GitHub（`gh auth login`）

## 执行步骤

1. 创建GitHub仓库
```bash
cd /Users/claw/sandbox/personal/claudflow
gh repo create ClaudeFlow --public --source=. --push
```

2. 确认仓库创建成功
```bash
gh repo view ClaudeFlow
```

3. 设置默认分支保护（可选）
```bash
gh branch protect main
```

## 验收标准

- GitHub仓库创建成功
- 本地代码已推送
- 仓库地址：`https://github.com/<your-username>/ClaudeFlow`

## 参考文档

- `/Users/claw/sandbox/personal/claudflow/docs/INDEX.md`