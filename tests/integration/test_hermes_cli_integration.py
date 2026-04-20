"""集成测试 - Hermes CLI完整工作流

V2.4.0核心测试：
- Hermes启动CLI并捕获session_id
- Hermes监控事件流并报告进度
- Hermes创建checkpoint
- Hermes干预会话（质量检查）
- Hermes检测任务完成

依赖：cli_driver.py
"""

import pytest
import subprocess
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List


class TestHermesStartSession:
    """Hermes启动CLI会话测试"""

    def test_hermes_start_session_mock(self):
        """测试：Hermes启动CLI并捕获session_id（Mock）"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        # Mock subprocess输出
        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = '{"type":"system","session_id":"test-session-12345"}\n'

        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock(stdout=mock_stdout)

            process, session_id = driver.start_session("测试任务")

            assert session_id == "test-session-12345"
            assert process is not None

    def test_hermes_session_id_persistence(self):
        """测试：session_id持久化存储"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = '{"session_id":"persist-test-id"}\n'

        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock(stdout=mock_stdout)

            process, session_id = driver.start_session("持久化测试")

            # 检查session存储
            stored = driver.get_session(session_id)
            assert stored is not None
            assert stored.session_id == "persist-test-id"


class TestHermesMonitorEvents:
    """Hermes监控事件流测试"""

    def test_hermes_monitor_tool_use_events(self):
        """测试：Hermes解析tool_use事件"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        # 构造tool_use事件
        tool_use_event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Glob", "id": "tool_001"}
                ]
            }
        }

        parsed = driver.parse_assistant_event(tool_use_event)

        assert parsed is not None
        assert parsed["type"] == "tool_use"
        assert parsed["tool_name"] == "Glob"

    def test_hermes_monitor_thinking_events(self):
        """测试：Hermes过滤thinking事件"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        thinking_event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "thinking", "thinking": "内部思考内容..."}
                ]
            }
        }

        parsed = driver.parse_assistant_event(thinking_event)

        assert parsed is not None
        assert parsed["type"] == "thinking"

    def test_hermes_monitor_text_events(self):
        """测试：Hermes识别text事件（阶段完成信号）"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        text_event = {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "阶段完成总结"}
                ]
            }
        }

        parsed = driver.parse_assistant_event(text_event)

        assert parsed is not None
        assert parsed["type"] == "text"
        assert parsed["text"] == "阶段完成总结"


class TestHermesCheckpointCreation:
    """Hermes创建checkpoint测试"""

    def test_hermes_checkpoint_on_phase_completion(self):
        """测试：阶段完成时创建checkpoint"""
        import tempfile
        from claudeflow.cli_driver import CliDriver
        from claudeflow.checkpoint import CheckpointManager

        driver = CliDriver()

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_mgr = CheckpointManager(checkpoint_dir=tmpdir)

            # 模拟阶段完成事件序列
            events = [
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write"}]}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "Phase1完成"}]}},
            ]

            # 检测text事件 → 触发checkpoint
            last_parsed = driver.parse_assistant_event(events[-1])
            if last_parsed and last_parsed["type"] == "text":
                checkpoint = checkpoint_mgr.save(
                    task_id="test-session",
                    phase="Phase1",
                    task_state={"summary": last_parsed["text"]},
                    execution_context={}
                )
                assert checkpoint is not None


class TestHermesIntervention:
    """Hermes干预会话测试"""

    def test_hermes_quality_check_intervention(self):
        """测试：质量检查干预"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        session_id = "quality-check-test"
        intervention_prompt = "请检查刚才完成的工作：代码是否符合规范？"

        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock(stdout=MagicMock())

            process = driver.intervene(session_id, intervention_prompt)

            # 验证命令参数
            call_args = mock_popen.call_args[0][0]
            assert "--resume" in call_args
            assert session_id in call_args
            assert intervention_prompt in call_args

    def test_hermes_user_input_intervention(self):
        """测试：用户输入注入干预"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        session_id = "user-input-test"
        user_input = "数据库连接信息: localhost:5432"
        intervention_prompt = f"用户提供了以下补充信息：\n{user_input}\n请继续执行任务。"

        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock(stdout=MagicMock())

            process = driver.intervene(session_id, intervention_prompt)

            call_args = mock_popen.call_args[0][0]
            assert "--resume" in call_args
            assert session_id in call_args
            # intervention_prompt包含用户输入
            assert user_input in intervention_prompt

    def test_hermes_intervention_requires_session_id(self):
        """测试：干预必须提供session_id"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        with pytest.raises(ValueError):
            driver.intervene("", "无效干预")


class TestHermesCompletionDetection:
    """Hermes检测任务完成测试"""

    def test_hermes_detect_success_completion(self):
        """测试：检测成功完成"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        events = [
            {"type": "assistant"},
            {"type": "result", "subtype": "success", "result": "任务执行成功"}
        ]

        is_complete, summary = driver.detect_completion(events)

        assert is_complete == True
        assert "成功" in summary

    def test_hermes_detect_error_completion(self):
        """测试：检测错误完成"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        events = [
            {"type": "assistant"},
            {"type": "result", "subtype": "error", "error": "执行失败"}
        ]

        is_complete, summary = driver.detect_completion(events)

        assert is_complete == True
        assert "错误" in summary

    def test_hermes_detect_not_complete(self):
        """测试：检测未完成"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        events = [
            {"type": "assistant"},
            {"type": "assistant"}
        ]

        is_complete, summary = driver.detect_completion(events)

        assert is_complete == False
        assert summary == ""


class TestHermesFullWorkflow:
    """Hermes完整工作流测试"""

    def test_hermes_full_workflow_mock(self):
        """测试：完整Hermes→CLI工作流（Mock）"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        # 1. 启动CLI
        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = '{"session_id":"workflow-test-id"}\n'
        mock_stdout.__iter__ = lambda self: iter([
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Glob"}]}}',
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read"}]}}',
            '{"type":"assistant","message":{"content":[{"type":"text","text":"Phase1完成"}]}}',
            '{"type":"result","subtype":"success","result":"任务完成"}',
        ])

        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock(stdout=mock_stdout)

            process, session_id = driver.start_session("完整工作流测试")

            assert session_id == "workflow-test-id"

            # 2. 监控事件流
            events = []
            for event in driver.monitor_events(process):
                events.append(event)

                parsed = driver.parse_assistant_event(event)
                if parsed and parsed["type"] == "tool_use":
                    # 进度追踪
                    pass

                # 3. 检测完成
                is_complete, summary = driver.detect_completion(events)
                if is_complete:
                    break

            assert is_complete == True


class TestHermesSubtaskCompletion:
    """Hermes子任务完成检测测试"""

    def test_hermes_detect_subtask_completion(self):
        """测试：子任务完成检测逻辑"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        # 子任务完成的典型事件序列
        events = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write"}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "子任务完成"}]}},
        ]

        # 检测text事件作为子任务完成信号
        last_event = events[-1]
        parsed = driver.parse_assistant_event(last_event)

        assert parsed["type"] == "text"
        assert "完成" in parsed["text"]


class TestHermesExceptionHandling:
    """Hermes异常处理测试"""

    def test_hermes_cli_crash_recovery(self):
        """测试：CLI崩溃恢复"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        # 模拟崩溃场景
        session_id = "crash-test"

        # 存储会话
        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = '{"session_id":"crash-test"}\n'

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock(stdout=mock_stdout, poll=Mock(return_value=None))
            mock_popen.return_value = mock_process

            process, _ = driver.start_session("崩溃测试")

            # 模拟崩溃后恢复
            recovery_prompt = "上次执行意外中断，请从checkpoint恢复"
            recovery_process = driver.intervene(session_id, recovery_prompt)

            assert recovery_process is not None

    def test_hermes_no_session_found(self):
        """测试：找不到会话"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        session = driver.get_session("nonexistent-session")

        assert session is None


class TestHermesProcessManagement:
    """Hermes进程管理测试"""

    def test_hermes_process_alive_check(self):
        """测试：进程存活检查"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        with patch('subprocess.Popen') as mock_popen:
            # Mock stdout.readline 返回字符串
            mock_stdout = MagicMock()
            mock_stdout.readline.return_value = '{"session_id":"alive-test"}\n'
            mock_process = Mock(stdout=mock_stdout, poll=Mock(return_value=None))  # 存活
            mock_popen.return_value = mock_process

            process, session_id = driver.start_session("存活检查")

            is_alive = driver.is_process_alive(session_id)
            assert is_alive == True

    def test_hermes_process_finished_check(self):
        """测试：进程结束检查"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        with patch('subprocess.Popen') as mock_popen:
            # Mock stdout.readline 返回字符串
            mock_stdout = MagicMock()
            mock_stdout.readline.return_value = '{"session_id":"finished-test"}\n'
            mock_process = Mock(stdout=mock_stdout, poll=Mock(return_value=0))  # 已结束
            mock_popen.return_value = mock_process

            process, session_id = driver.start_session("结束检查")

            is_alive = driver.is_process_alive(session_id)
            assert is_alive == False

    def test_hermes_clear_session(self):
        """测试：清除会话"""
        from claudeflow.cli_driver import CliDriver

        driver = CliDriver()

        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = '{"session_id":"clear-test"}\n'

        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock(
                stdout=mock_stdout,
                poll=Mock(return_value=None),
                terminate=Mock()
            )
            mock_popen.return_value = mock_process

            process, session_id = driver.start_session("清除测试")

            # 清除会话
            driver.clear_session(session_id)

            # 验证已清除
            session = driver.get_session(session_id)
            assert session is None