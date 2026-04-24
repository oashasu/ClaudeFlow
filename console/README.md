# ClaudeFlow Console

前端控制台目前分成两层：

- `Dashboard / TaskDetail`
  - 旧任务流视图
  - 侧重任务状态、阶段、checkpoint、SSE 进度
- `Runtime Console` (`/runtime`)
  - 新 runtime 工作台
  - 侧重 `status / sessions / plan / explain / dispatch`

## Runtime Console 当前能力

- sample / live 双模式
- 自动刷新与轮询间隔
- runtime 总览
- session 列表
- session 动作：
  - `解释任务`
  - `查看事件`
  - `发送干预`
  - `标记完成`
  - `标记失败`
- session inspector
- `Dashboard / TaskDetail` 到 Runtime Console 的导航入口

## 文档要求

凡是修改以下文件或功能时，必须同步更新主仓文档：

- `src/views/RuntimeConsole.vue`
- `src/components/runtime/**`
- `src/services/runtimeApi.ts`

对应文档入口：

- `../docs/09_Runtime实现与变更记录.md`
