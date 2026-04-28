#!/bin/bash
# verify-doc-consistency.sh - 校验 INDEX.md / changelog.md / pipeline-state.json 三者口径一致
#
# 用法: scripts/verify-doc-consistency.sh [phase_id]
# 示例: scripts/verify-doc-consistency.sh phase-5
#
# 通过标准:
#   - INDEX.md 与 changelog.md Phase 状态描述一致
#   - pipeline-state.json phase 状态与文档口径一致
#   - 输出 CONSISTENCY CHECK PASSED

set -e

PHASE_ID="${1:-phase-5}"
PIPELINE_STATE=".super-dev/pipeline-state.json"
INDEX_MD="docs/INDEX.md"
CHANGELOG_MD="docs/runtime/changelog.md"

# 检查文件存在
if [[ ! -f "$PIPELINE_STATE" ]]; then
    echo "ERROR: $PIPELINE_STATE not found"
    exit 1
fi

if [[ ! -f "$INDEX_MD" ]]; then
    echo "ERROR: $INDEX_MD not found"
    exit 1
fi

if [[ ! -f "$CHANGELOG_MD" ]]; then
    echo "ERROR: $CHANGELOG_MD not found"
    exit 1
fi

echo "=== Document Consistency Check for $PHASE_ID ==="

# 1. 从 pipeline-state.json 提取 phase 状态
PIPELINE_STATUS=$(python3 -c "
import json
with open('$PIPELINE_STATE') as f:
    data = json.load(f)
phase = data['phases'].get('$PHASE_ID', {})
print(phase.get('status', 'not_found'))
")

echo "pipeline-state.json: $PHASE_ID.status = $PIPELINE_STATUS"

# 转换 phase_id 格式: phase-4 -> Phase 4
PHASE_DISPLAY=$(echo "$PHASE_ID" | sed 's/phase-/Phase /')

# 2. 从 INDEX.md 提取 Phase 状态
# 格式: | V3.X | ... | Phase X 进行中/已完成/accepted |
INDEX_STATUS=$(grep "$PHASE_DISPLAY" "$INDEX_MD" | grep -oE "进行中|已完成|accepted|in_execution" | head -1 || echo "not_found")

if [[ -z "$INDEX_STATUS" ]]; then
    INDEX_STATUS="not_found"
fi

echo "INDEX.md: $PHASE_DISPLAY status = $INDEX_STATUS"

# 3. 从 changelog.md 提取 Phase 状态
# 只匹配阶段总记录标题格式: ## YYYY-MM-DD Phase X: ...
# 不匹配历史子小节: ### Phase X: xxx
CHANGELOG_STATUS=$(grep -E "^## [0-9]{4}-[0-9]{2}-[0-9]{2} $PHASE_DISPLAY:" "$CHANGELOG_MD" | tail -1 | grep -oE "进行中|已完成|accepted|收口" || echo "not_found")

if [[ -z "$CHANGELOG_STATUS" ]]; then
    CHANGELOG_STATUS="not_found"
fi

echo "changelog.md: $PHASE_DISPLAY status = $CHANGELOG_STATUS"

# 4. 状态映射校验
# pipeline-state.json 的 in_execution 对应文档的"进行中"
# pipeline-state.json 的 accepted/completed 对应文档的"已完成/accepted/收口"

STATUS_MATCH=true

# 校验 pipeline-state.json vs INDEX.md
case "$PIPELINE_STATUS" in
    "in_execution")
        if [[ "$INDEX_STATUS" != "进行中" && "$INDEX_STATUS" != "in_execution" ]]; then
            echo "MISMATCH: pipeline=in_execution vs INDEX=$INDEX_STATUS"
            STATUS_MATCH=false
        fi
        ;;
    "accepted"|"completed")
        if [[ "$INDEX_STATUS" != "已完成" && "$INDEX_STATUS" != "accepted" && "$INDEX_STATUS" != "收口" ]]; then
            echo "MISMATCH: pipeline=$PIPELINE_STATUS vs INDEX=$INDEX_STATUS"
            STATUS_MATCH=false
        fi
        ;;
    *)
        echo "WARN: Unknown pipeline status: $PIPELINE_STATUS"
        ;;
esac

# 校验 pipeline-state.json vs changelog.md
case "$PIPELINE_STATUS" in
    "in_execution")
        if [[ "$CHANGELOG_STATUS" != "进行中" && "$CHANGELOG_STATUS" != "in_execution" ]]; then
            echo "MISMATCH: pipeline=in_execution vs CHANGELOG=$CHANGELOG_STATUS"
            STATUS_MATCH=false
        fi
        ;;
    "accepted"|"completed")
        if [[ "$CHANGELOG_STATUS" != "已完成" && "$CHANGELOG_STATUS" != "accepted" && "$CHANGELOG_STATUS" != "收口" ]]; then
            echo "MISMATCH: pipeline=$PIPELINE_STATUS vs CHANGELOG=$CHANGELOG_STATUS"
            STATUS_MATCH=false
        fi
        ;;
    *)
        # 已在上面处理
        ;;
esac

# 5. 最终判断
if [[ "$STATUS_MATCH" == "true" ]]; then
    echo ""
    echo "=== CONSISTENCY CHECK PASSED ==="
    exit 0
else
    echo ""
    echo "=== CONSISTENCY CHECK FAILED ==="
    echo "Please align phase status across INDEX.md, changelog.md, and pipeline-state.json"
    exit 1
fi