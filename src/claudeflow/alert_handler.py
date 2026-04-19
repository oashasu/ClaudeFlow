"""告警处理器 - 告警处理（人工介入/文件损坏/死循环）

V2新增模块：
- 发送告警消息到WebSocket
- 支持多种告警类型
- 文件损坏告警、人工介入请求、死循环告警
"""

from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional

from claudeflow.websocket_client import WebSocketClient, WebSocketState


class AlertSeverity(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertMessage:
    """告警消息数据结构"""

    type: str = "alert"
    severity: AlertSeverity = AlertSeverity.WARNING
    task_id: str = ""
    message: str = ""
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass
class FileCorruptAlert:
    """文件损坏告警数据结构"""

    type: str = "file_corrupt_alert"
    severity: AlertSeverity = AlertSeverity.WARNING
    file_path: str = ""
    error_type: str = ""
    module: str = ""
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass
class InterventionRequestAlert:
    """人工介入请求告警数据结构"""

    type: str = "intervention_request"
    severity: AlertSeverity = AlertSeverity.CRITICAL
    task_id: str = ""
    reason: str = ""
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


class AlertHandler:
    """告警处理器"""

    def __init__(self, ws_client: WebSocketClient):
        """
        初始化告警处理器

        Args:
            ws_client: WebSocket客户端
        """
        self.ws_client = ws_client

    async def send_file_corrupt_alert(
        self,
        file_path: str,
        error_type: str,
        module: str
    ) -> None:
        """
        发送文件损坏告警

        Args:
            file_path: 损坏文件路径
            error_type: 错误类型
            module: 所属模块
        """
        if self.ws_client.state != WebSocketState.CONNECTED:
            return

        alert = FileCorruptAlert(
            file_path=file_path,
            error_type=error_type,
            module=module
        )
        await self.ws_client.send(alert.to_dict())

    async def send_intervention_request(
        self,
        task_id: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发送人工介入请求

        Args:
            task_id: 任务ID
            reason: 介入原因
            context: 上下文信息
        """
        if self.ws_client.state != WebSocketState.CONNECTED:
            return

        alert = InterventionRequestAlert(
            task_id=task_id,
            reason=reason,
            context=context
        )
        await self.ws_client.send(alert.to_dict())

    async def send_dead_loop_alert(
        self,
        task_id: str,
        content: str,
        count: int
    ) -> None:
        """
        发送死循环告警

        Args:
            task_id: 任务ID
            content: 重复内容
            count: 重复次数
        """
        if self.ws_client.state != WebSocketState.CONNECTED:
            return

        msg = {
            "type": "log_alert",
            "alert_level": "WARNING",
            "task_id": task_id,
            "message": "检测到thinking死循环",
            "duplicate_content": content[:500],
            "duplicate_count": count,
            "timestamp": datetime.now().isoformat()
        }
        await self.ws_client.send(msg)

    async def send_alert(
        self,
        severity: AlertSeverity,
        task_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发送通用告警

        Args:
            severity: 告警级别
            task_id: 任务ID
            message: 告警消息
            context: 上下文信息
        """
        if self.ws_client.state != WebSocketState.CONNECTED:
            return

        alert = AlertMessage(
            severity=severity,
            task_id=task_id,
            message=message,
            context=context
        )
        await self.ws_client.send(alert.to_dict())