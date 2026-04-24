# Runtime 协议与 Schema 校验规格

> 状态：`pending`
>
> 优先级：`P1`

## 1. 目标

固化 runtime 关键返回体，降低前后端协议漂移和 silent failure 风险。

## 2. 覆盖对象

- `status`
- `sessions`
- `plan`
- `explain`
- `dispatch`
- `session events`

## 3. 要求

### 3.1 后端协议稳定化

后端对以上对象应有稳定字段集合，不允许无说明地删改关键字段。

### 3.2 示例与 schema 同步

以下文件必须同步维护：

- `examples/runtime-*.schema.json`
- `examples/runtime-*.sample.json`

### 3.3 前端校验

前端消费 live payload 时，应在进入视图前完成 parse/validate。  
当 payload 不符合约定结构时，必须明确报错。

## 4. 非目标

- 不追求本阶段覆盖所有历史遗留 Java API
- 不在本阶段重写全部旧 console 类型定义

## 5. 严格验收标准

1. `status / sessions / plan / explain / dispatch / session events` 均有对应 schema 或明确的类型约束定义。
2. 每个 schema 至少有一份 sample 与之对应，且 sample 能被当前前端成功解析。
3. 任一 live payload 缺少关键字段时，前端必须报出可识别错误，不能静默渲染空视图。
4. 协议变更时，必须同步更新：
   - schema
   - sample
   - 实现记录文档
5. 至少补充：
   - schema/sample 一致性测试
   - 前端 parse 失败测试
   - 后端返回体结构测试
