#!/bin/bash
# run-release-gates.sh - 统一执行 Gate 1-6 发布门禁
#
# 用法: scripts/run-release-gates.sh
#
# 通过标准: 所有 6 门禁全部 passed
# 失败定位: 输出失败门禁编号与命令，便于排查
#
# 参考: docs/operations/release-gate-matrix.md

GATE_PASSED=0
GATE_FAILED=0
FAILED_GATES=""

echo "=== ClaudeFlow Release Gates ==="
echo "执行顺序: Gate 1 -> Gate 2 -> Gate 3 -> Gate 4 -> Gate 5 -> Gate 6"
echo ""

# Gate 1: 前端测试
echo "[Gate 1] 前端测试..."
cd console && npm test -- --run 2>&1 | tee /tmp/gate1.log || true; cd ..
if grep -qE "Tests\s+[0-9]+ passed" /tmp/gate1.log && ! grep -qE "FAIL\s+[0-9]+|✗|Error:" /tmp/gate1.log; then
    echo "[Gate 1] PASSED"
    GATE_PASSED=$((GATE_PASSED + 1))
else
    echo "[Gate 1] FAILED - 检查 /tmp/gate1.log"
    FAILED_GATES="$FAILED_GATES Gate1"
    GATE_FAILED=$((GATE_FAILED + 1))
fi
echo ""

# Gate 2: Python 核心
echo "[Gate 2] Python 核心..."
PYTHONPATH=src python3 -m pytest tests/unit/test_runtime_api.py tests/unit/test_cli.py tests/unit/test_runtime_manager.py tests/unit/test_phase_gate_service.py -v 2>&1 | tee /tmp/gate2.log || true
if grep -qE "[0-9]+ passed" /tmp/gate2.log && ! grep -qE "FAILED|ERROR" /tmp/gate2.log; then
    echo "[Gate 2] PASSED"
    GATE_PASSED=$((GATE_PASSED + 1))
else
    echo "[Gate 2] FAILED - 检查 /tmp/gate2.log"
    FAILED_GATES="$FAILED_GATES Gate2"
    GATE_FAILED=$((GATE_FAILED + 1))
fi
echo ""

# Gate 3: Java 测试
echo "[Gate 3] Java 测试..."
mvn test 2>&1 | tee /tmp/gate3.log || true
# 判断标准：BUILD SUCCESS + Failures: 0, Errors: 0（不匹配业务日志级 ERROR）
if grep -q "BUILD SUCCESS" /tmp/gate3.log && grep -qE "Failures: 0, Errors: 0" /tmp/gate3.log && ! grep -q "BUILD FAILURE" /tmp/gate3.log; then
    echo "[Gate 3] PASSED"
    GATE_PASSED=$((GATE_PASSED + 1))
else
    echo "[Gate 3] FAILED - 检查 /tmp/gate3.log"
    FAILED_GATES="$FAILED_GATES Gate3"
    GATE_FAILED=$((GATE_FAILED + 1))
fi
echo ""

# Gate 4: Python 回归
echo "[Gate 4] Python 回归..."
PYTHONPATH=src python3 -m pytest tests/unit/ -v --ignore=tests/unit/governance/ --ignore=tests/unit/test_employee_pool.py --ignore=tests/unit/test_knowledge_retrieval.py --ignore=tests/unit/test_phase_reviewer.py --ignore=tests/unit/test_task_reviewer.py --ignore=tests/unit/test_progress_reporter.py 2>&1 | tee /tmp/gate4.log || true
if grep -qE "[0-9]+ passed" /tmp/gate4.log && ! grep -qE "FAILED|ERROR" /tmp/gate4.log; then
    echo "[Gate 4] PASSED"
    GATE_PASSED=$((GATE_PASSED + 1))
else
    echo "[Gate 4] FAILED - 检查 /tmp/gate4.log"
    FAILED_GATES="$FAILED_GATES Gate4"
    GATE_FAILED=$((GATE_FAILED + 1))
fi
echo ""

# Gate 5: Runtime Smoke
echo "[Gate 5] Runtime Smoke..."
PYTHONPATH=src python3 scripts/runtime_smoke.py 2>&1 | tee /tmp/gate5.log || true
if grep -q "Smoke test PASSED" /tmp/gate5.log; then
    echo "[Gate 5] PASSED"
    GATE_PASSED=$((GATE_PASSED + 1))
else
    echo "[Gate 5] FAILED - 检查 /tmp/gate5.log"
    FAILED_GATES="$FAILED_GATES Gate5"
    GATE_FAILED=$((GATE_FAILED + 1))
fi
echo ""

# Gate 6: 文档一致性
echo "[Gate 6] 文档一致性..."
bash scripts/verify-doc-consistency.sh 2>&1 | tee /tmp/gate6.log || true
if grep -q "CONSISTENCY CHECK PASSED" /tmp/gate6.log; then
    echo "[Gate 6] PASSED"
    GATE_PASSED=$((GATE_PASSED + 1))
else
    echo "[Gate 6] FAILED - 检查 /tmp/gate6.log"
    FAILED_GATES="$FAILED_GATES Gate6"
    GATE_FAILED=$((GATE_FAILED + 1))
fi
echo ""

# 最终汇总
echo "=== Release Gates Summary ==="
echo "Passed: $GATE_PASSED / 6"
echo "Failed: $GATE_FAILED / 6"

if [[ "$GATE_FAILED" -eq 0 ]]; then
    echo ""
    echo "=== ALL GATES PASSED ==="
    echo "Decision: release-ready"
    exit 0
else
    echo ""
    echo "=== SOME GATES FAILED ==="
    echo "Failed gates: $FAILED_GATES"
    echo "Decision: not-ready"
    echo ""
    echo "排查建议:"
    echo "  - Gate 1 失败: cat /tmp/gate1.log | grep -E 'FAIL|✗|Error'"
    echo "  - Gate 2 失败: cat /tmp/gate2.log | grep -E 'FAILED|ERROR'"
    echo "  - Gate 3 失败: cat /tmp/gate3.log | grep -E 'FAILURE|ERROR'"
    echo "  - Gate 4 失败: cat /tmp/gate4.log | grep -E 'FAILED|ERROR'"
    echo "  - Gate 5 失败: cat /tmp/gate5.log | grep -i fail"
    echo "  - Gate 6 失败: cat /tmp/gate6.log | grep -i mismatch"
    exit 1
fi