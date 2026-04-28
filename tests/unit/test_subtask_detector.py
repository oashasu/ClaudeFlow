"""子任务检测器单元测试（V2.1.0新增）"""

import pytest
from claudeflow.subtask_detector import (
    SubtaskDetector,
    CompletionType,
    SubtaskCompletionResult
)


class TestExplicitMarkerDetection:
    """显式标记检测测试"""

    def test_detect_subtask_complete_marker(self):
        """测试：检测SUBTASK_COMPLETE标记"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "工作完成\n# SUBTASK_COMPLETE"
        )
        assert result.is_complete is True
        assert result.completion_type == CompletionType.EXPLICIT_MARKER

    def test_detect_complete_marker(self):
        """测试：检测COMPLETE标记"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "# COMPLETE"
        )
        assert result.is_complete is True
        assert result.completion_type == CompletionType.EXPLICIT_MARKER

    def test_detect_done_marker(self):
        """测试：检测DONE标记"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "# DONE"
        )
        assert result.is_complete is True
        assert result.completion_type == CompletionType.EXPLICIT_MARKER

    def test_marker_details(self):
        """测试：标记检测结果包含详情"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "# SUBTASK_COMPLETE"
        )
        assert result.details is not None
        assert "SUBTASK_COMPLETE" in result.details


class TestTestsPassedDetection:
    """测试通过检测"""

    def test_detect_pytest_passed(self):
        """测试：检测pytest passed输出"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "pytest output:\n5 passed, 0 failed"
        )
        assert result.is_complete is True
        assert result.completion_type == CompletionType.TESTS_PASSED

    def test_detect_pytest_passed_with_count(self):
        """测试：提取passed数量"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "pytest results: 12 passed in 3.5s"
        )
        assert result.is_complete is True
        assert "12" in result.details

    def test_detect_from_tool_results(self):
        """测试：从工具结果检测pytest"""
        detector = SubtaskDetector()
        tool_results = [
            {
                "tool_name": "Bash",
                "command": "pytest tests/",
                "output": "3 passed"
            }
        ]
        result = detector.detect_completion(
            "task_001",
            "",
            tool_results=tool_results
        )
        assert result.is_complete is True
        assert result.completion_type == CompletionType.TESTS_PASSED

    def test_no_tests_passed_without_pytest(self):
        """测试：非pytest输出不误判"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "passed the exam"
        )
        assert result.is_complete is False


class TestFileCreatedDetection:
    """文件创建检测"""

    def test_detect_file_created(self):
        """测试：检测文件创建完成"""
        detector = SubtaskDetector()
        tool_results = [
            {
                "tool_name": "Write",
                "file_path": "/path/to/file.py"
            }
        ]
        result = detector.detect_completion(
            "task_001",
            "",
            tool_results=tool_results
        )
        assert result.is_complete is True
        assert result.completion_type == CompletionType.FILE_CREATED

    def test_file_created_details(self):
        """测试：文件创建详情"""
        detector = SubtaskDetector()
        tool_results = [
            {"tool_name": "Write", "file_path": "/a.py"},
            {"tool_name": "Write", "file_path": "/b.py"}
        ]
        result = detector.detect_completion(
            "task_001",
            "",
            tool_results=tool_results
        )
        assert "2个" in result.details

    def test_pending_edits_blocks_completion(self):
        """测试：pending edits阻止判定完成"""
        detector = SubtaskDetector()
        detector.register_pending_edit("task_001", "/pending.py")

        tool_results = [
            {"tool_name": "Write", "file_path": "/done.py"}
        ]
        result = detector.detect_completion(
            "task_001",
            "",
            tool_results=tool_results
        )
        assert result.is_complete is False

    def test_no_file_created(self):
        """测试：无文件创建不误判"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "no files created"
        )
        assert result.is_complete is False


class TestCompletionPriority:
    """检测优先级测试"""

    def test_explicit_marker_priority_highest(self):
        """测试：显式标记优先级最高"""
        detector = SubtaskDetector()
        # 同时包含pytest和marker
        output = "pytest passed\n# SUBTASK_COMPLETE"
        result = detector.detect_completion("task_001", output)
        # 应返回显式标记而非pytest
        assert result.completion_type == CompletionType.EXPLICIT_MARKER

    def test_tests_passed_priority_second(self):
        """测试：测试通过优先级第二"""
        detector = SubtaskDetector()
        tool_results = [
            {"tool_name": "Write", "file_path": "/file.py"}
        ]
        output = "pytest passed"
        result = detector.detect_completion(
            "task_001", output, tool_results
        )
        # pytest优先于文件创建
        assert result.completion_type == CompletionType.TESTS_PASSED


class TestPendingEditsManagement:
    """待处理编辑管理"""

    def test_register_pending_edit(self):
        """测试：注册待处理编辑"""
        detector = SubtaskDetector()
        detector.register_pending_edit("task_001", "/file.py")

        pending = detector.get_pending_edits("task_001")
        assert "/file.py" in pending

    def test_clear_pending_edits(self):
        """测试：清除待处理编辑"""
        detector = SubtaskDetector()
        detector.register_pending_edit("task_001", "/file.py")
        detector.clear_pending_edits("task_001")

        pending = detector.get_pending_edits("task_001")
        assert len(pending) == 0

    def test_pending_edits_per_task(self):
        """测试：每个任务独立pending列表"""
        detector = SubtaskDetector()
        detector.register_pending_edit("task_001", "/a.py")
        detector.register_pending_edit("task_002", "/b.py")

        pending1 = detector.get_pending_edits("task_001")
        pending2 = detector.get_pending_edits("task_002")

        assert "/a.py" in pending1
        assert "/b.py" not in pending1
        assert "/b.py" in pending2


class TestNotComplete:
    """未完成情况"""

    def test_empty_output_not_complete(self):
        """测试：空输出不完成"""
        detector = SubtaskDetector()
        result = detector.detect_completion("task_001", "")
        assert result.is_complete is False
        assert result.completion_type == CompletionType.NOT_COMPLETE

    def test_partial_work_not_complete(self):
        """测试：部分工作不完成"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "正在开发中..."
        )
        assert result.is_complete is False

    def test_no_tool_results_not_complete(self):
        """测试：无工具结果不完成"""
        detector = SubtaskDetector()
        result = detector.detect_completion(
            "task_001",
            "output",
            tool_results=None
        )
        assert result.is_complete is False