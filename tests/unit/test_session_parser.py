"""session_parser模块测试 - 解析.jsonl + 工具摘要"""

import os
import json
import tempfile
import pytest
from datetime import datetime

from claudeflow.session_parser import (
    SessionParser,
    ToolCall,
    extract_action_from_tool
)


class TestToolCall:
    """工具调用数据结构测试"""

    def test_tool_call_creation(self):
        """测试工具调用创建"""
        tool_call = ToolCall(
            timestamp="2026-04-19T10:30:00Z",
            tool_name="Read",
            tool_input={"file_path": "/path/to/file.py"}
        )
        assert tool_call.tool_name == "Read"
        assert tool_call.tool_input["file_path"] == "/path/to/file.py"

    def test_tool_call_to_dict(self):
        """测试序列化"""
        tool_call = ToolCall(
            timestamp="2026-04-19T10:30:00Z",
            tool_name="Edit",
            tool_input={"file_path": "/path/to/file.py", "old_string": "a", "new_string": "b"}
        )
        data = tool_call.to_dict()
        assert data["tool_name"] == "Edit"
        assert data["summary"] is not None


class TestExtractActionFromTool:
    """工具摘要提取测试"""

    def test_read_tool_summary(self):
        """测试Read工具摘要"""
        summary = extract_action_from_tool("Read", {"file_path": "/path/to/state_machine.py"})
        assert summary == "正在读取 state_machine.py"

    def test_edit_tool_summary(self):
        """测试Edit工具摘要"""
        summary = extract_action_from_tool("Edit", {"file_path": "/path/to/checkpoint.py"})
        assert summary == "正在修改 checkpoint.py"

    def test_write_tool_summary(self):
        """测试Write工具摘要"""
        summary = extract_action_from_tool("Write", {"file_path": "/path/to/new_file.py"})
        assert summary == "正在创建 new_file.py"

    def test_bash_pytest_summary(self):
        """测试Bash pytest摘要"""
        summary = extract_action_from_tool("Bash", {"command": "pytest tests/ -v"})
        assert summary == "正在运行测试"

    def test_bash_git_summary(self):
        """测试Bash git摘要"""
        summary = extract_action_from_tool("Bash", {"command": "git status"})
        assert summary == "正在执行Git操作"

    def test_bash_other_summary(self):
        """测试Bash其他命令摘要"""
        summary = extract_action_from_tool("Bash", {"command": "ls -la very_long_command_here"})
        assert "正在执行" in summary
        assert len(summary) <= 40  # 截断长度限制

    def test_grep_tool_summary(self):
        """测试Grep工具摘要"""
        summary = extract_action_from_tool("Grep", {"pattern": "def test_something"})
        assert "正在搜索" in summary

    def test_glob_tool_summary(self):
        """测试Glob工具摘要"""
        summary = extract_action_from_tool("Glob", {"pattern": "**/*.py"})
        assert "正在查找文件" in summary

    def test_unknown_tool_summary(self):
        """测试未知工具摘要"""
        summary = extract_action_from_tool("UnknownTool", {})
        assert "正在执行 UnknownTool" in summary


class TestSessionParser:
    """Session解析器测试"""

    @pytest.fixture
    def temp_jsonl_file(self):
        """创建临时.jsonl文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # 写入测试数据
            messages = [
                {"type": "user", "timestamp": "2026-04-19T10:00:00Z", "content": "开始任务"},
                {"type": "assistant", "timestamp": "2026-04-19T10:01:00Z", "content": "好的"},
                {"type": "tool_use", "timestamp": "2026-04-19T10:02:00Z", "tool_name": "Read", "tool_input": {"file_path": "/path/to/file.py"}},
                {"type": "tool_result", "timestamp": "2026-04-19T10:03:00Z", "tool_result": "file content"},
                {"type": "tool_use", "timestamp": "2026-04-19T10:04:00Z", "tool_name": "Edit", "tool_input": {"file_path": "/path/to/file.py"}},
                {"type": "system", "timestamp": "2026-04-19T10:05:00Z", "content": "系统消息"}
            ]
            for msg in messages:
                f.write(json.dumps(msg) + '\n')
            filepath = f.name

        yield filepath
        os.unlink(filepath)

    def test_parse_jsonl_basic(self, temp_jsonl_file):
        """测试基本解析"""
        parser = SessionParser(temp_jsonl_file)
        tool_calls = parser.extract_tool_calls()

        assert len(tool_calls) == 2
        assert tool_calls[0].tool_name == "Read"
        assert tool_calls[1].tool_name == "Edit"

    def test_parse_jsonl_no_tool_calls(self):
        """测试无工具调用的文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            messages = [
                {"type": "user", "timestamp": "2026-04-19T10:00:00Z", "content": "开始"},
                {"type": "assistant", "timestamp": "2026-04-19T10:01:00Z", "content": "回复"}
            ]
            for msg in messages:
                f.write(json.dumps(msg) + '\n')
            filepath = f.name

        parser = SessionParser(filepath)
        tool_calls = parser.extract_tool_calls()
        assert len(tool_calls) == 0

        os.unlink(filepath)

    def test_parse_jsonl_invalid_file(self):
        """测试无效文件处理"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("invalid json line\n")
            f.write("{\"type\": \"tool_use\", \"tool_name\": \"Read\"}\n")
            filepath = f.name

        parser = SessionParser(filepath)
        tool_calls = parser.extract_tool_calls()

        # 应该跳过无效行，只解析有效行
        assert len(tool_calls) == 1

        os.unlink(filepath)

    def test_generate_summary_report(self, temp_jsonl_file):
        """测试生成摘要报告"""
        parser = SessionParser(temp_jsonl_file)
        report = parser.generate_summary_report()

        assert report["total_tool_calls"] == 2
        assert report["tool_types"]["Read"] == 1
        assert report["tool_types"]["Edit"] == 1
        assert len(report["summaries"]) == 2

    def test_parse_nonexistent_file(self):
        """测试不存在文件"""
        parser = SessionParser("/nonexistent/path/file.jsonl")
        tool_calls = parser.extract_tool_calls()
        assert len(tool_calls) == 0

    def test_extract_all_messages(self, temp_jsonl_file):
        """测试提取所有消息"""
        parser = SessionParser(temp_jsonl_file)
        messages = parser.extract_all_messages()

        assert len(messages) == 6
        types = [m["type"] for m in messages]
        assert "user" in types
        assert "assistant" in types
        assert "tool_use" in types
        assert "tool_result" in types
        assert "system" in types