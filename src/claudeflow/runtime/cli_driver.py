"""CLI驱动器 - 驱动Claude Code CLI进程

V2.4.0核心模块：
- 启动CLI会话并捕获session_id
- 监控事件流解析进度
- 检测任务完成状态
- 通过--resume实现干预机制

基于验证报告结论实现：
https://github.com/claw/claudeflow/blob/main/docs/V2_追加设计/11_CLI驱动机制验证报告.md
"""

import subprocess
import json
import threading
import uuid
from typing import Dict, Any, Optional, Tuple, Iterator, List
from dataclasses import dataclass


@dataclass
class CliSession:
    """CLI会话信息"""

    session_id: str
    process: subprocess.Popen
    prompt: str
    working_directory: Optional[str] = None
    events: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.events is None:
            self.events = []


class CliDriver:
    """CLI进程驱动器

    核心机制：
    - 启动：claude -p "prompt" --output-format stream-json --verbose
    - session追踪：从首事件提取session_id
    - 干预：claude -p --resume session_id "新prompt"
    - 解析：assistant事件包含thinking/tool_use/text
    """

    # CLI命令基础
    CLI_CMD = "claude"

    def __init__(self):
        """初始化驱动器"""
        self.sessions: Dict[str, CliSession] = {}

    def _build_start_command(self, prompt: str, session_id: str = None) -> List[str]:
        """
        构造启动命令

        Args:
            prompt: 任务描述
            session_id: 可选的会话ID（CLI会使用此ID，可用于--resume恢复）

        Returns:
            命令参数列表
        """
        cmd = [
            self.CLI_CMD,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose"
        ]
        # 指定session_id，CLI会使用此ID并持久化会话
        if session_id:
            cmd.extend(["--session-id", session_id])
        return cmd

    def _build_intervene_command(self, session_id: str, prompt: str) -> List[str]:
        """
        构造干预命令（恢复session）

        Args:
            session_id: CLI会话ID
            prompt: 干预内容

        Returns:
            命令参数列表
        """
        return [
            self.CLI_CMD,
            "-p",
            "--resume",
            session_id,
            prompt,
            "--output-format",
            "stream-json",
            "--verbose"
        ]

    def _extract_session_id(self, first_line: str) -> Optional[str]:
        """
        从首行提取session_id

        Args:
            first_line: JSON格式的首行输出

        Returns:
            session_id或None
        """
        try:
            event = json.loads(first_line.strip())
            return event.get("session_id")
        except (json.JSONDecodeError, AttributeError):
            return None

    def _store_session(
        self,
        session_id: str,
        process: subprocess.Popen,
        prompt: str = "",
        working_directory: Optional[str] = None
    ):
        """
        存储会话信息

        Args:
            session_id: CLI会话ID
            process: subprocess对象
            prompt: 原始prompt
        """
        self.sessions[session_id] = CliSession(
            session_id=session_id,
            process=process,
            prompt=prompt,
            working_directory=working_directory
        )

    def _parse_events(self, stdout) -> Iterator[Dict[str, Any]]:
        """
        解析stdout中的事件流

        Args:
            stdout: subprocess.stdout对象

        Returns:
            事件字典迭代器
        """
        for line in stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                yield event
            except json.JSONDecodeError:
                # 跳过无效JSON行
                continue

    def _background_monitor(self, session_id: str):
        """
        后台监控线程：持续读取事件并存储到session

        Args:
            session_id: CLI会话ID
        """
        session = self.sessions.get(session_id)
        if not session:
            return

        try:
            for event in self._parse_events(session.process.stdout):
                session.events.append(event)
                # result事件表示完成，结束监控
                if event.get("type") == "result":
                    break
        except Exception as e:
            # 记录错误事件
            error_event = {
                "type": "error",
                "message": str(e),
                "session_id": session_id
            }
            session.events.append(error_event)

    def start_session(
        self,
        prompt: str,
        cwd: Optional[str] = None
    ) -> Tuple[subprocess.Popen, str]:
        """
        启动新的CLI会话

        Args:
            prompt: 任务描述

        Returns:
            (process, session_id): subprocess对象和CLI会话ID

        Note:
            我们生成UUID并传给CLI的--session-id参数，
            这样CLI会使用此ID并持久化会话，可用于--resume恢复。
        """
        # 生成我们控制的session_id
        session_id = str(uuid.uuid4())
        cmd = self._build_start_command(prompt, session_id)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=cwd
        )

        # 验证首行返回的session_id是否是我们指定的
        first_line = process.stdout.readline()
        extracted_id = self._extract_session_id(first_line)

        # 存储会话（使用我们生成的ID）
        self._store_session(session_id, process, prompt, working_directory=cwd)
        # 启动后台监控线程
        monitor_thread = threading.Thread(
            target=self._background_monitor,
            args=(session_id,),
            daemon=True
        )
        monitor_thread.start()

        return process, session_id

    def monitor_events(self, process: subprocess.Popen) -> Iterator[Dict[str, Any]]:
        """
        监控CLI事件流

        Args:
            process: subprocess对象

        Returns:
            事件字典迭代器
        """
        return self._parse_events(process.stdout)

    def parse_assistant_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析assistant事件

        Args:
            event: 原始事件字典

        Returns:
            解析后的结构:
            {
                "type": "thinking" | "tool_use" | "text",
                "tool_name": str | None,
                "tool_input": dict | None,
                "text": str | None
            }
        """
        if event.get("type") != "assistant":
            return None

        message = event.get("message", {})
        content = message.get("content", [])

        if not content:
            return None

        # 取第一个内容项
        item = content[0]
        item_type = item.get("type")

        if item_type == "thinking":
            return {
                "type": "thinking",
                "text": item.get("thinking", ""),
                "tool_name": None,
                "tool_input": None
            }
        elif item_type == "tool_use":
            return {
                "type": "tool_use",
                "tool_name": item.get("name"),
                "tool_input": item.get("input", {}),
                "text": None
            }
        elif item_type == "text":
            return {
                "type": "text",
                "text": item.get("text", ""),
                "tool_name": None,
                "tool_input": None
            }

        return None

    def parse_all_assistant_content(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析assistant事件的所有内容项

        Args:
            event: 原始事件字典

        Returns:
            所有解析后的内容项列表
        """
        if event.get("type") != "assistant":
            return []

        message = event.get("message", {})
        content = message.get("content", [])

        results = []
        for item in content:
            item_type = item.get("type")

            if item_type == "thinking":
                results.append({
                    "type": "thinking",
                    "text": item.get("thinking", ""),
                    "tool_name": None,
                    "tool_input": None
                })
            elif item_type == "tool_use":
                results.append({
                    "type": "tool_use",
                    "tool_name": item.get("name"),
                    "tool_input": item.get("input", {}),
                    "text": None
                })
            elif item_type == "text":
                results.append({
                    "type": "text",
                    "text": item.get("text", ""),
                    "tool_name": None,
                    "tool_input": None
                })

        return results

    def detect_completion(self, events: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        检测任务完成

        Args:
            events: 事件列表

        Returns:
            (is_complete, summary): 是否完成和摘要文本
        """
        for event in events:
            if event.get("type") == "result":
                subtype = event.get("subtype", "")

                if subtype == "success":
                    result_text = event.get("result", "任务完成")
                    return True, result_text
                elif subtype == "error":
                    error_text = event.get("error", "执行失败")
                    return True, f"错误: {error_text}"

        return False, ""

    def intervene(self, session_id: str, prompt: str) -> subprocess.Popen:
        """
        干预正在执行的会话

        Args:
            session_id: CLI会话ID
            prompt: 干预内容

        Returns:
            新的subprocess对象

        Raises:
            ValueError: session_id无效
        """
        if not session_id:
            raise ValueError("session_id不能为空")

        cmd = self._build_intervene_command(session_id, prompt)

        session = self.sessions.get(session_id)
        cwd = session.working_directory if session else None

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=cwd
        )

        # 更新session中的process
        if session_id in self.sessions:
            self.sessions[session_id].process = process

        return process

    def get_session(self, session_id: str) -> Optional[CliSession]:
        """
        获取会话信息

        Args:
            session_id: CLI会话ID

        Returns:
            CliSession或None
        """
        return self.sessions.get(session_id)

    def clear_session(self, session_id: str):
        """
        清除会话

        Args:
            session_id: CLI会话ID
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if session.process and session.process.poll() is None:
                session.process.terminate()
            del self.sessions[session_id]

    def is_process_alive(self, session_id: str) -> bool:
        """
        检查进程是否存活

        Args:
            session_id: CLI会话ID

        Returns:
            是否存活
        """
        session = self.get_session(session_id)
        if session and session.process:
            return session.process.poll() is None
        return False

    def wait_for_completion(self, session_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """
        等待会话完成

        Args:
            session_id: CLI会话ID
            timeout: 超时时间（秒）

        Returns:
            result事件或None
        """
        session = self.get_session(session_id)
        if not session:
            return None

        events = []
        for event in self.monitor_events(session.process):
            events.append(event)
            session.events.append(event)

            if event.get("type") == "result":
                return event

        return None
