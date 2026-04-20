"""WebSocket客户端 - WebSocket通信（Python→Java）

V2新增模块：
- WebSocket连接管理
- 断线重连机制
- 消息发送/接收
- sessionId自动获取与传递
"""

import json
import asyncio
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Callable

from .session_utils import get_current_session_id

# websockets库可选，Mock测试时不需要
try:
    import websockets
except ImportError:
    websockets = None


class WebSocketState(Enum):
    """WebSocket连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"


@dataclass
class WebSocketConfig:
    """WebSocket配置"""

    uri: str = "ws://localhost:8080/ws/hermes"
    reconnect_max_attempts: int = 5
    reconnect_base_delay: float = 1.0  # 秒
    reconnect_max_delay: float = 30.0  # 秒


class WebSocketClient:
    """WebSocket客户端"""

    def __init__(self, config: Optional[WebSocketConfig] = None, project_dir: Optional[str] = None):
        """
        初始化客户端

        Args:
            config: 配置对象
            project_dir: 项目目录（用于获取sessionId）
        """
        self.config = config or WebSocketConfig()
        self.project_dir = project_dir
        self.session_id: Optional[str] = None
        self.ws: Optional[Any] = None
        self.state = WebSocketState.DISCONNECTED
        self._message_callback: Optional[Callable] = None

    async def connect(self, worker_id: str, task_id: str) -> bool:
        """
        连接WebSocket

        Args:
            worker_id: Worker ID
            task_id: 任务ID

        Returns:
            bool: 是否成功连接
        """
        if websockets is None:
            # 无websockets库时返回False（用于测试环境）
            return False

        try:
            self.state = WebSocketState.CONNECTING
            self.ws = await websockets.connect(self.config.uri)

            # 获取当前sessionId
            self.session_id = get_current_session_id(self.project_dir)

            # 发送注册消息（包含sessionId）
            await self.send({
                "type": "worker_register",
                "worker_id": worker_id,
                "task_id": task_id,
                "session_id": self.session_id
            })

            self.state = WebSocketState.CONNECTED
            return True

        except Exception:
            self.state = WebSocketState.DISCONNECTED
            return False

    async def connect_with_retry(self, worker_id: str, task_id: str) -> bool:
        """
        带重连的连接

        Args:
            worker_id: Worker ID
            task_id: 任务ID

        Returns:
            bool: 是否成功连接
        """
        attempt = 0

        while attempt < self.config.reconnect_max_attempts:
            result = await self.connect(worker_id, task_id)
            if result:
                return True

            attempt += 1
            # 指数退避
            delay = min(
                self.config.reconnect_base_delay * (2 ** attempt),
                self.config.reconnect_max_delay
            )
            await asyncio.sleep(delay)

        return False

    async def send(self, message: Dict[str, Any]) -> None:
        """
        发送消息

        Args:
            message: 消息字典
        """
        if self.state != WebSocketState.CONNECTED or self.ws is None:
            return

        try:
            await self.ws.send(json.dumps(message))
        except Exception:
            # 发送失败，不抛异常
            pass

    async def listen(self) -> None:
        """
        监听消息
        """
        if self.ws is None:
            return

        try:
            async for msg in self.ws:
                data = json.loads(msg)
                if self._message_callback:
                    await self._message_callback(data)
        except Exception:
            self.state = WebSocketState.DISCONNECTED

    def on_message(self, callback: Callable) -> None:
        """
        设置消息回调

        Args:
            callback: 回调函数
        """
        self._message_callback = callback

    async def close(self) -> None:
        """
        关闭连接
        """
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass

        self.ws = None
        self.state = WebSocketState.DISCONNECTED

    def get_state(self) -> WebSocketState:
        """
        获取当前状态

        Returns:
            WebSocketState: 当前状态
        """
        return self.state