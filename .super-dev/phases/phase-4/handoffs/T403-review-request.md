# T403 Handoff Review Request

## 任务完成摘要

**任务**: T403 - 收口 live data parse validate 错误路径与状态断言

**验收目标**:
- A42: composable 测试运行在标准 Vue setup/harness 中
- A43: live payload parse/validate 失败路径可断言、可回归、可预测

## 实现内容

### 新增测试文件

- `console/tests/runtimeLiveDataValidation.spec.ts` 新增 24 个测试（原 6 个，现 30 个）
  - parsePlan computed property 错误路径（4 tests）
  - parseExplain computed property 错误路径（3 tests）
  - parseDispatch computed property 错误路径（3 tests）
  - loadLivePlan API + parse 失败路径（3 tests）
  - loadLiveExplain API + parse 失败路径（3 tests）
  - runLiveDispatch API + parse 失败路径（3 tests）
  - loadLiveStatus API 失败路径（2 tests）
  - loadLiveSessionEvents API 失败路径（1 test）
  - 状态断言完整性验证（2 tests）

### 测试覆盖要点

1. **computed property 惰性触发验证**
   - Vue computed 是惰性的，需要先访问 computed.value 才触发 parse/validate
   - 测试断言顺序调整：先访问 computed，再检查 parseError

2. **parseError 与 liveError 区分明确**
   - parseError: JSON 解析/协议校验失败（可预测的协议错误）
   - liveError: API 网络请求失败（不可预测的运行时错误）
   - sessionEventsError: session 事件专属错误域

3. **不静默降级**
   - 无效 payload 导致 computed 返回 null
   - parseError 被明确设置，不隐藏错误
   - 状态字段清空，不保留旧值

## 验收证据

### A42 验证
```bash
cd console && npm test -- --run tests/runtimeLiveDataValidation.spec.ts
# 输出：30 tests passed
# 全部使用 withComposable() 在 Vue setup 上下文中运行
# 使用 captureWarnings() 验证无 lifecycle warning
```

### A43 验证
```bash
cd console && npm test -- --run tests/runtimeLiveDataValidation.spec.ts
# 输出：30 tests passed
# 覆盖：
# - parsePlan/parseExplain/parseDispatch computed 错误路径
# - loadLivePlan/loadLiveExplain/runLiveDispatch API + parse 失败
# - loadLiveStatus/loadLiveSessionEvents API 失败
# - 状态断言完整性验证
```

## 测试结果

```
Test Files  11 passed (11)
     Tests  104 passed (104)
```

## 关键变更点

1. **runtimeLiveDataValidation.spec.ts 增强**
   - 从 6 tests 扩展到 30 tests
   - 覆盖所有 parse/validate 错误路径
   - 使用 flushPromises() 确保异步完成

2. **无修改 useRuntimeLiveData.ts**
   - parseError/liveError 区分已正确实现
   - computed property 惰性触发是 Vue 设计，非 bug

3. **无修改 runtimeValidator.ts**
   - validator 返回 'JSON 结构不符合预期协议' 是正确消息
   - 测试断言匹配实际返回值

## Blocker 检查

无 blocker：
- 所有 composable 测试运行在 Vue setup 上下文 ✅
- parse/validate 失败路径可断言 ✅
- 无静默降级，无效 payload 返回 null ✅
- 无 lifecycle warning 噪音 ✅

## 下一步

请求 governor review T403，确认 A42/A43 验收通过。