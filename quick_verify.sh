#!/bin/bash
# ClaudeFlow V2.4.0 快速验证脚本

echo "========================================"
echo "ClaudeFlow V2.4.0 快速验证"
echo "========================================"

cd /Users/claw/sandbox/personal/claudeflow
export PYTHONPATH=/Users/claw/sandbox/personal/claudeflow/src

echo ""
echo "[1] cli_driver单元测试..."
python3 -m pytest tests/unit/test_cli_driver.py -v --tb=short -q 2>&1 | tail -5

echo ""
echo "[2] cli_driver覆盖率..."
python3 -m pytest tests/unit/test_cli_driver.py --cov=claudeflow.cli_driver --cov-report=term --cov-fail-under=0 2>&1 | grep -E "(TOTAL|passed)"

echo ""
echo "[3] CLAUDE.md指令集检查..."
if grep -q "任务调度管理系统" CLAUDE.md; then
    echo "✓ Hermes指令集已注入"
    grep "核心职责" CLAUDE.md | head -1
else
    echo "✗ Hermes指令集未找到"
fi

echo ""
echo "[4] 项目结构检查..."
ls -la src/claudeflow/cli_driver.py 2>/dev/null && echo "✓ cli_driver.py存在" || echo "✗ cli_driver.py不存在"
ls -la console/src/views/Dashboard.vue 2>/dev/null && echo "✓ Dashboard.vue存在" || echo "✗ Dashboard.vue不存在"

echo ""
echo "========================================"
echo "验证完成"
echo "========================================"
echo ""
echo "下一步："
echo "  1. 详细验证: python3 verify_cli_driver.py"
echo "  2. 查看手册: cat /Users/claw/sandbox/tasks/2026-04-18_ClaudeFlow系统设计/10_验证手册/Hermes_CLI驱动验证操作指南.md"