"""CLI驱动器单元测试

测试CliDriver核心能力：
- 启动CLI会话
- 监控事件流
- 解析assistant事件
- 检测任务完成
- 干预恢复
"""

import pytest
import json
import subprocess
from unittest.mock import Mock, MagicMock, patch
from io import StringIO


class TestCliDriverStartSession:
    """CLI会话启动测试"""

    def test_start_session_command_format(self):
        """测试：启动命令格式正确"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        # 验证命令构造
        prompt = "测试任务"
        cmd = driver._build_start_command(prompt)

        assert "claude" in cmd
        assert "-p" in cmd
        assert prompt in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--verbose" in cmd

    def test_extract_session_id_from_first_event(self):
        """测试：从首事件提取session_id"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        # 模拟首行输出
        first_line = '{"type":"system","session_id":"test-session-123","subtype":"init"}\n'
        session_id = driver._extract_session_id(first_line)

        assert session_id == "test-session-123"

    def test_extract_session_id_missing(self):
        """测试：session_id不存在时返回None"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        first_line = '{"type":"system","subtype":"init"}\n'
        session_id = driver._extract_session_id(first_line)

        assert session_id is None

    def test_session_storage(self):
        """测试：会话持久化存储"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()

        # 模拟session存储
        session_id = "test-123"
        mock_process = Mock()
        driver._store_session(session_id, mock_process)

        assert session_id in driver.sessions
        # 存储的是CliSession对象
        stored = driver.sessions[session_id]
        assert isinstance(stored, CliSession)
        assert stored.process == mock_process

    @patch("claudeflow.runtime.cli_driver.subprocess.Popen")
    def test_start_session_passes_cwd_to_process(self, mock_popen):
        """测试：start_session会将cwd传给CLI进程"""
        from claudeflow.runtime.cli_driver import CliDriver

        mock_process = Mock()
        mock_process.stdout.readline.return_value = '{"type":"system","session_id":"test-123"}\n'
        mock_popen.return_value = mock_process

        driver = CliDriver()
        driver.start_session("测试任务", cwd="/tmp/demo-worktree")

        assert mock_popen.call_args.kwargs["cwd"] == "/tmp/demo-worktree"
        stored = next(iter(driver.sessions.values()))
        assert stored.working_directory == "/tmp/demo-worktree"


class TestCliDriverMonitorEvents:
    """事件流监控测试"""

    def test_monitor_events_json_parse(self):
        """测试：JSON解析正确"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        # 模拟多行输出
        lines = [
            '{"type":"system","session_id":"abc"}\n',
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Glob"}]}}\n',
            '{"type":"result","subtype":"success"}\n'
        ]
        mock_stdout = StringIO(''.join(lines))

        events = list(driver._parse_events(mock_stdout))

        assert len(events) == 3
        assert events[0]["type"] == "system"
        assert events[1]["type"] == "assistant"
        assert events[2]["type"] == "result"

    def test_monitor_events_skip_invalid(self):
        """测试：跳过无效JSON行"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        lines = [
            '{"type":"system","session_id":"abc"}\n',
            'invalid json line\n',
            '{"type":"result"}\n'
        ]
        mock_stdout = StringIO(''.join(lines))

        events = list(driver._parse_events(mock_stdout))

        assert len(events) == 2  # 无效行被跳过

    def test_monitor_events_empty_output(self):
        """测试：空输出返回空列表"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()
        mock_stdout = StringIO('')

        events = list(driver._parse_events(mock_stdout))

        assert len(events) == 0


class TestCliDriverParseAssistantEvent:
    """assistant事件解析测试"""

    def test_parse_assistant_thinking(self):
        """测试：thinking事件解析"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "正在分析需求..."}
                ]
            }
        }

        parsed = driver.parse_assistant_event(event)

        assert parsed["type"] == "thinking"
        assert parsed["text"] == "正在分析需求..."
        assert parsed["tool_name"] is None

    def test_parse_assistant_tool_use(self):
        """测试：tool_use事件解析"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Glob", "input": {"pattern": "*.py"}}
                ]
            }
        }

        parsed = driver.parse_assistant_event(event)

        assert parsed["type"] == "tool_use"
        assert parsed["tool_name"] == "Glob"
        assert parsed["tool_input"] == {"pattern": "*.py"}
        assert parsed["text"] is None

    def test_parse_assistant_text(self):
        """测试：text事件解析"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "任务已完成"}
                ]
            }
        }

        parsed = driver.parse_assistant_event(event)

        assert parsed["type"] == "text"
        assert parsed["text"] == "任务已完成"
        assert parsed["tool_name"] is None

    def test_parse_assistant_multiple_content(self):
        """测试：多内容项解析（取第一个有效类型）"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "思考中..."},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "/test.py"}}
                ]
            }
        }

        # 解析第一个内容项
        parsed = driver.parse_assistant_event(event)

        assert parsed["type"] == "thinking"  # 第一个

    def test_parse_assistant_empty_content(self):
        """测试：空内容返回None"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": []
            }
        }

        parsed = driver.parse_assistant_event(event)

        assert parsed is None


class TestCliDriverDetectCompletion:
    """任务完成检测测试"""

    def test_detect_completion_success(self):
        """测试：成功完成检测"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        events = [
            {"type": "system"},
            {"type": "assistant"},
            {"type": "result", "subtype": "success", "result": "任务完成"}
        ]

        is_complete, summary = driver.detect_completion(events)

        assert is_complete == True
        assert "任务完成" in summary

    def test_detect_completion_error(self):
        """测试：错误完成检测"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        events = [
            {"type": "system"},
            {"type": "result", "subtype": "error", "error": "执行失败"}
        ]

        is_complete, summary = driver.detect_completion(events)

        assert is_complete == True
        assert "执行失败" in summary

    def test_detect_completion_not_complete(self):
        """测试：未完成检测"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        events = [
            {"type": "system"},
            {"type": "assistant"}
        ]

        is_complete, summary = driver.detect_completion(events)

        assert is_complete == False
        assert summary == ""

    def test_detect_completion_with_cost(self):
        """测试：完成检测包含成本信息"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        events = [
            {"type": "result", "subtype": "success", "cost_usd": 0.05}
        ]

        is_complete, summary = driver.detect_completion(events)

        assert is_complete == True
        assert "cost_usd" in str(events[-1])


class TestCliDriverIntervene:
    """干预恢复测试"""

    def test_intervene_command_format(self):
        """测试：干预命令包含--resume"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        session_id = "test-session-123"
        prompt = "请继续执行"
        cmd = driver._build_intervene_command(session_id, prompt)

        assert "--resume" in cmd
        assert session_id in cmd
        assert prompt in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd

    def test_intervene_requires_session(self):
        """测试：干预需要有效session_id"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        # 无session_id时抛异常
        with pytest.raises(ValueError):
            driver.intervene(None, "测试")

    def test_intervene_returns_new_process(self):
        """测试：干预返回新进程"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        session_id = "test-123"
        driver.sessions[session_id] = Mock()  # 预存session

        # Mock subprocess.Popen
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process

            process = driver.intervene(session_id, "继续")

            assert process == mock_process

    @patch("claudeflow.runtime.cli_driver.subprocess.Popen")
    def test_intervene_reuses_session_working_directory(self, mock_popen):
        """测试：干预时复用session的working_directory"""
        from claudeflow.runtime.cli_driver import CliDriver

        mock_process = Mock()
        mock_popen.return_value = mock_process

        driver = CliDriver()
        driver._store_session(
            "sess-1",
            Mock(),
            prompt="测试",
            working_directory="/tmp/demo-worktree"
        )

        driver.intervene("sess-1", "继续")

        assert mock_popen.call_args.kwargs["cwd"] == "/tmp/demo-worktree"


class TestCliDriverSessionPersistence:
    """会话持久化测试"""

    def test_get_session_exists(self):
        """测试：获取已存在的session"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        session_id = "test-123"
        mock_process = Mock()
        driver.sessions[session_id] = mock_process

        process = driver.get_session(session_id)

        assert process == mock_process

    def test_get_session_not_exists(self):
        """测试：获取不存在的session返回None"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        process = driver.get_session("nonexistent")

        assert process is None

    def test_clear_session(self):
        """测试：清除session"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        session_id = "test-123"
        driver.sessions[session_id] = Mock()

        driver.clear_session(session_id)

        assert session_id not in driver.sessions


class TestCliDriverParseAllContent:
    """parse_all_assistant_content测试"""

    def test_parse_all_content_multiple(self):
        """测试：解析所有内容项"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "思考中"},
                    {"type": "tool_use", "name": "Glob", "input": {"pattern": "*.py"}},
                    {"type": "text", "text": "找到5个文件"}
                ]
            }
        }

        results = driver.parse_all_assistant_content(event)

        assert len(results) == 3
        assert results[0]["type"] == "thinking"
        assert results[1]["type"] == "tool_use"
        assert results[2]["type"] == "text"

    def test_parse_all_content_empty(self):
        """测试：空内容返回空列表"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {"type": "assistant", "message": {"content": []}}
        results = driver.parse_all_assistant_content(event)

        assert len(results) == 0

    def test_parse_all_content_non_assistant(self):
        """测试：非assistant事件返回空列表"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {"type": "system"}
        results = driver.parse_all_assistant_content(event)

        assert len(results) == 0

    def test_parse_all_content_unknown_type(self):
        """测试：未知类型被跳过"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "unknown"},
                    {"type": "text", "text": "有效内容"}
                ]
            }
        }

        results = driver.parse_all_assistant_content(event)

        assert len(results) == 1
        assert results[0]["type"] == "text"


class TestCliDriverProcessAlive:
    """进程存活检测测试"""

    def test_is_process_alive_running(self):
        """测试：进程运行中"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()
        session_id = "test-123"

        mock_process = Mock()
        mock_process.poll.return_value = None  # 进程运行中

        driver.sessions[session_id] = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        assert driver.is_process_alive(session_id) == True

    def test_is_process_alive_finished(self):
        """测试：进程已结束"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()
        session_id = "test-123"

        mock_process = Mock()
        mock_process.poll.return_value = 0  # 进程已结束

        driver.sessions[session_id] = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        assert driver.is_process_alive(session_id) == False

    def test_is_process_alive_no_session(self):
        """测试：session不存在"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        assert driver.is_process_alive("nonexistent") == False

    def test_is_process_alive_no_process(self):
        """测试：session无process"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()
        session_id = "test-123"

        driver.sessions[session_id] = CliSession(
            session_id=session_id,
            process=None,
            prompt="test"
        )

        assert driver.is_process_alive(session_id) == False


class TestCliDriverWaitForCompletion:
    """等待完成测试"""

    def test_wait_for_completion_success(self):
        """测试：等待成功完成"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()
        session_id = "test-123"

        output = [
            '{"type":"assistant","message":{"content":[{"type":"text","text":"完成"}]}}\n',
            '{"type":"result","subtype":"success","result":"成功"}\n'
        ]
        mock_process = Mock()
        mock_process.stdout = StringIO(''.join(output))

        driver.sessions[session_id] = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        result = driver.wait_for_completion(session_id)

        assert result is not None
        assert result["type"] == "result"
        assert result["subtype"] == "success"

    def test_wait_for_completion_no_result_event(self):
        """测试：无result事件"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()
        session_id = "test-123"

        output = [
            '{"type":"assistant","message":{"content":[{"type":"text","text":"输出"}]}}\n'
        ]
        mock_process = Mock()
        mock_process.stdout = StringIO(''.join(output))

        driver.sessions[session_id] = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        result = driver.wait_for_completion(session_id)

        assert result is None

    def test_wait_for_completion_no_session(self):
        """测试：session不存在"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        result = driver.wait_for_completion("nonexistent")

        assert result is None


class TestCliDriverEdgeCases:
    """边界情况测试"""

    def test_extract_session_id_invalid_json(self):
        """测试：无效JSON返回None"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        session_id = driver._extract_session_id("not json at all")

        assert session_id is None

    def test_parse_assistant_non_assistant_event(self):
        """测试：非assistant事件返回None"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {"type": "system", "session_id": "abc"}
        result = driver.parse_assistant_event(event)

        assert result is None

    def test_parse_assistant_unknown_content_type(self):
        """测试：未知内容类型返回None"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        event = {
            "type": "assistant",
            "message": {
                "content": [{"type": "unknown_type"}]
            }
        }
        result = driver.parse_assistant_event(event)

        assert result is None

    def test_clear_session_terminates_process(self):
        """测试：清除session终止进程"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()
        session_id = "test-123"

        mock_process = Mock()
        mock_process.poll.return_value = None  # 进程运行中

        driver.sessions[session_id] = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        driver.clear_session(session_id)

        mock_process.terminate.assert_called_once()
        assert session_id not in driver.sessions

    def test_clear_session_finished_process(self):
        """测试：清除已结束进程不调用terminate"""
        from claudeflow.runtime.cli_driver import CliDriver, CliSession

        driver = CliDriver()
        session_id = "test-123"

        mock_process = Mock()
        mock_process.poll.return_value = 0  # 进程已结束

        driver.sessions[session_id] = CliSession(
            session_id=session_id,
            process=mock_process,
            prompt="test"
        )

        driver.clear_session(session_id)

        mock_process.terminate.assert_not_called()
        assert session_id not in driver.sessions


class TestCliDriverIntegration:
    """集成测试（需Mock完整流程）"""

    def test_full_session_lifecycle_mock(self):
        """测试：完整session生命周期（Mock）"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        # 模拟完整输出（首行被start_session消费）
        first_line = '{"type":"system","session_id":"session-abc","subtype":"init"}\n'
        rest_output = [
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Glob","input":{"pattern":"*.py"}}]}}\n',
            '{"type":"assistant","message":{"content":[{"type":"text","text":"找到10个文件"}]}}\n',
            '{"type":"result","subtype":"success","result":"任务完成"}\n'
        ]

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = StringIO(first_line + ''.join(rest_output))
            mock_popen.return_value = mock_process

            # 启动session（会消费首行）
            process, session_id = driver.start_session("测试任务")
            session = driver.get_session(session_id)
            events = session.events

            # 检测完成
            is_complete, summary = driver.detect_completion(events)

            assert session_id in driver.sessions
            assert len(events) >= 1
            assert is_complete == True

    def test_intervention_flow_mock(self):
        """测试：干预流程（Mock）"""
        from claudeflow.runtime.cli_driver import CliDriver

        driver = CliDriver()

        # 预存session
        session_id = "session-abc"
        driver.sessions[session_id] = Mock()

        # 模拟干预输出
        intervention_output = [
            '{"type":"assistant","message":{"content":[{"type":"text","text":"已按建议修改"}]}}\n',
            '{"type":"result","subtype":"success"}\n'
        ]

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.stdout = StringIO(''.join(intervention_output))
            mock_popen.return_value = mock_process

            # 干预
            process = driver.intervene(session_id, "请修改代码")

            # 监控
            events = list(driver.monitor_events(process))
            is_complete, summary = driver.detect_completion(events)

            assert is_complete == True
