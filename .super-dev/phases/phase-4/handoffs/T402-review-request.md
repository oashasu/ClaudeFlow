# T402 Handoff Review Request

## 任务完成摘要

**任务**: T402 - 清理 Runtime Console warning 并稳定 action audit 测试隔离

**验收目标**:
- A41: 前端 warning 收口 - action-audit fetch warning 不再作为默认测试噪音
- A43: Audit / Live Data 错误路径稳定 - 成功、空数据、失败路径都有稳定断言

## 实现内容

### 新增测试文件
- `console/tests/runtimeActionAudit.spec.ts` (10 tests)
  - 成功路径测试：listActionAudit 返回正确数据
  - 空数据路径测试：空数组不产生错误
  - 失败路径测试：API 失败抛出正确错误
  - session action 成功/失败路径测试
  - useRuntimeActions loadActionHistory 隔离测试

### 测试覆盖
- `runtimeActionAudit.spec.ts`: 10 tests (新增)
- `RuntimeConsole.spec.ts`: 11 tests (继承，正确 mock 配置)
- 总计: 80 tests passed

## 验收证据

### A41 验证
```bash
cd console && npm test -- --run tests/RuntimeConsole.spec.ts 2>&1 | grep -i "warn"
# 输出：无 warning

# RuntimeConsole.spec.ts:137 正确配置 mock:
vi.mocked(runtimeApi.listActionAudit).mockResolvedValue(defaultMockAuditRecords)
```

### A43 验证
```bash
cd console && npm test -- --run tests/runtimeActionAudit.spec.ts
# 输出：10 tests passed
# 覆盖：
# - 成功路径：listActionAudit 成功返回
# - 空数据路径：空数组处理
# - 失败路径：API 失败抛出错误
# - loadActionHistory 隔离：成功/失败/空数据场景
```

## 测试结果

```
Test Files  11 passed (11)
     Tests  80 passed (80)
```

## 关键变更点

1. **新增 runtimeActionAudit.spec.ts**
   - 专门测试 action audit 的各种路径
   - 使用 captureWarnings() 验证 console.warn 隔离
   - 使用 withComposable() 在 Vue setup 上下文测试 useRuntimeActions

2. **无修改 useRuntimeActions.ts**
   - console.warn 在错误路径是预期行为（A43 要求失败路径可断言）
   - 成功路径通过正确 mock 配置避免触发 warning

## Blocker 检查

无 blocker：
- 前端测试默认运行不打印 audit fetch warning ✅
- action audit 成功/空数据/失败路径都有断言 ✅
- 未删除错误路径断言，正确测试隔离 ✅

## 下一步

请求 governor review T402，确认 A41/A43 验收通过。