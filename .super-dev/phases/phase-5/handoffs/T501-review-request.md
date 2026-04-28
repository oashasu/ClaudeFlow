# T501 Review Request (Rework Round 3)

> 任务: 固化 release checklist 与 quality gate 矩阵
> 提交时间: 2026-04-28T07:30:00Z
> 执行者: Claude宿主
> 审查者: Governor
> 返工轮次: 3

---

## 返工修复

### Blocker: changelog 匹配策略不稳定 - 已修复

| 原问题 | 修复内容 |
|--------|----------|
| `grep "$PHASE_DISPLAY" | head -1` 会抓到历史子小节 | 改为 `grep -E "^## YYYY-MM-DD Phase X:" | tail -1` |

**修复位置**: `scripts/verify-doc-consistency.sh` 第 61-67 行
- 正则匹配只匹配阶段总记录标题格式 `^## [0-9]{4}-[0-9]{2}-[0-9]{2} Phase X:`
- 使用 `tail -1` 取最新的阶段总记录，而不是 `head -1` 取最早的

---

## 交付产物

| 文件 | 说明 |
|------|------|
| docs/operations/release-checklist.md | 7阶段发布前检查清单（含 Java + Gate 1-6） |
| docs/operations/release-gate-matrix.md | 6门禁矩阵定义 |
| scripts/verify-doc-consistency.sh | 文档一致性校验脚本（稳定三方校验） |

---

## Acceptance Coverage

### A51 Release Checklist 固化

| 要求 | 覆盖情况 |
|------|----------|
| 仓库内存在明确的发布前 checklist | docs/operations/release-checklist.md 存在 ✅ |
| checklist 覆盖 Python | Phase 2/4 覆盖 ✅ |
| checklist 覆盖 Console | Phase 1 覆盖 ✅ |
| checklist 覆盖 Java | Phase 3 覆盖 ✅ |
| checklist 覆盖 smoke | Phase 5 覆盖 ✅ |
| checklist 覆盖文档一致性检查 | Phase 6 覆盖 ✅ |
| 发布决策标准与 gate matrix 一致 | Gate 1-6 口径闭环 ✅ |

### A52 Quality Gate 统一入口

| 要求 | 覆盖情况 |
|------|----------|
| 发布前门禁命令有统一入口 | release-gate-matrix.md 定义 6 门禁 ✅ |
| 门禁顺序明确 | Gate 1-6 顺序固定 ✅ |
| 可复跑 | 所有命令引用仓库内真实可执行命令 ✅ |
| 可被 governor 直接引用 | Governor 引用约定已定义 ✅ |
| Gate 6 真实校验三方一致性 | scripts/verify-doc-consistency.sh 稳定匹配阶段总记录 ✅ |

---

## changelog 匹配逻辑

**修复前**:
```bash
grep "$PHASE_DISPLAY" "$CHANGELOG_MD" | head -1
```
问题：会匹配到历史子小节 `### Phase 4: 兼容层 wrapper 清理 ✅`

**修复后**:
```bash
grep -E "^## [0-9]{4}-[0-9]{2}-[0-9]{2} $PHASE_DISPLAY:" "$CHANGELOG_MD" | tail -1
```
优势：
- 只匹配阶段总记录标题格式 `## YYYY-MM-DD Phase X:`
- 取最新的阶段总记录（如有多次记录）

---

## 验证结果

```bash
# phase-4 测试
scripts/verify-doc-consistency.sh phase-4
# 输出:
# changelog.md: Phase 4 status = 收口 (正确匹配阶段总记录)
# MISMATCH: pipeline=accepted vs INDEX=进行中 (真实暴露 INDEX.md 未同步)

# phase-5 测试
scripts/verify-doc-consistency.sh phase-5
# 输出:
# INDEX.md: Phase 5 status = not_found (真实暴露 Phase 5 文档尚未同步)
# changelog.md: Phase 5 status = not_found
```

脚本本身可执行，能真实暴露文档不一致情况。

---

## 自检清单

- [x] changelog 匹配限定到阶段总记录标题格式
- [x] 使用 `tail -1` 取最新，不误抓历史子小节
- [x] 三方一致性校验逻辑完整
- [x] Java 门禁使用仓库真实 `mvn test` 命令
- [x] 发布决策标准改为 Gate 1-6
- [x] blocker/non-blocker/warning budget 分层清晰

---

## 请求 Governor Review

请验证以下内容：

1. A51: release-checklist.md 发布决策标准是否与 gate matrix 一致（Gate 1-6）
2. A52: verify-doc-consistency.sh 是否稳定匹配阶段总记录，不误抓历史子小节
3. 所有 blocker 是否已修复

---

**Decision Request**: A51/A52 是否 accepted?