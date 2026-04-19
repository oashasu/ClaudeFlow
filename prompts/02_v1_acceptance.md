# 阶段2：V1验收

## 任务目标

验收V1最小版本，确认核心功能和TDD流程可行。

## 前置条件

- V1开发完成
- 所有模块已实现

## 执行步骤

### Step 1：运行全部测试

```bash
cd /Users/claw/sandbox/personal/claudflow
pytest tests/ -v --cov=src/claudflow --cov-report=html
```

### Step 2：验证覆盖率

```bash
# 查看覆盖率报告
open htmlcov/index.html
```

确认覆盖率 >= 80%

### Step 3：CLI功能测试

```bash
# 安装CLI
pip install -e .

# 测试CLI命令
claudflow create "测试任务"
claudflow list
claudflow status <task_id>
```

### Step 4：生成验收报告

创建验收文档：
```markdown
# ClaudeFlow V1验收报告

## 测试统计
- 单元测试：XXX个
- 集成测试：XXX个
- E2E测试：XXX个
- 覆盖率：XX%

## 功能验收
- [ ] CLI可用
- [ ] 任务创建
- [ ] 任务查询
- [ ] 状态流转
- [ ] Checkpoint保存/恢复

## TDD流程验证
- [ ] 先写测试可行
- [ ] 测试驱动实现可行
- [ ] 覆盖率达标

## 下一步
- V2扩展设计
```

## 验收标准

- 全部测试通过
- 覆盖率 >= 80%
- CLI可用
- TDD流程验证可行

## 通过后

进入阶段3：V2扩展