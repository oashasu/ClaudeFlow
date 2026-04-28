"""进度报告器 - 进度推送WebSocket

V2新增模块：
- 发送进度更新到WebSocket
- 发送工具调用摘要
- 发送阶段完成通知
"""

import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from claudeflow.websocket_client import WebSocketClient, WebSocketState


@dataclass
class ProgressMessage:
    """进度消息数据结构"""

    type: str = "progress"
    task_id: str = ""
    phase: str = ""
    progress: int = 0
    message: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return asdict(self)


@dataclass
class ToolCallMessage:
    """工具调用消息数据结构"""

    type: str = "tool_call_summary"
    task_id: str = ""
    tool_name: str = ""
    action: str = ""
    file_path: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return asdict(self)


class ProgressReporter:
    """进度报告器"""

    def __init__(self, ws_client: WebSocketClient):
        """
        初始化进度报告器

        Args:
            ws_client: WebSocket客户端
        """
        self.ws_client = ws_client

    async def send_progress(
        self,
        task_id: str,
        phase: str,
        progress: int,
        message: Optional[str] = None
    ) -> None:
        """
        发送进度更新

        Args:
            task_id: 任务ID
            phase: 当前阶段
            progress: 进度百分比
            message: 进度消息
        """
        if self.ws_client.state != WebSocketState.CONNECTED:
            return

        msg = ProgressMessage(
            task_id=task_id,
            phase=phase,
            progress=progress,
            message=message
        )
        await self.ws_client.send(msg.to_dict())

    async def send_tool_call(
        self,
        task_id: str,
        tool_name: str,
        action: str,
        file_path: Optional[str] = None
    ) -> None:
        """
        发送工具调用摘要

        Args:
            task_id: 任务ID
            tool_name: 工具名称
            action: 动作描述
            file_path: 文件路径（可选）
        """
        if self.ws_client.state != WebSocketState.CONNECTED:
            return

        msg = ToolCallMessage(
            task_id=task_id,
            tool_name=tool_name,
            action=action,
            file_path=file_path
        )
        await self.ws_client.send(msg.to_dict())

    async def send_phase_complete(
        self,
        task_id: str,
        phase: str,
        summary: str
    ) -> None:
        """
        发送阶段完成通知

        Args:
            task_id: 任务ID
            phase: 阶段名称
            summary: 阶段总结
        """
        if self.ws_client.state != WebSocketState.CONNECTED:
            return

        msg = {
            "type": "phase_complete",
            "task_id": task_id,
            "phase": phase,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        await self.ws_client.send(msg)