"""Hermes服务 - FastAPI CLI驱动服务

V2.5.0核心模块：
- 提供4个API端点供Web调用
- SSE事件流实时推送进度
- 封装cli_driver的subprocess能力

设计文档：
https://github.com/claw/claudeflow/blob/main/docs/V2_追加设计/11_CLI驱动机制验证报告.md
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio

from claudeflow.cli_driver import CliDriver


# 请求模型
class StartRequest(BaseModel):
    """启动会话请求"""
    prompt: str = Field(..., min_length=1, description="任务描述")


class InterveneRequest(BaseModel):
    """干预会话请求"""
    prompt: str = Field(..., min_length=1, description="干预内容")


# 响应模型
class SessionResponse(BaseModel):
    """会话响应"""
    session_id: str
    status: str


class StatusResponse(BaseModel):
    """状态响应"""
    session_id: str
    status: str
    events_count: int = 0


# 全局驱动器实例
driver = CliDriver()

# FastAPI应用
app = FastAPI(
    title="ClaudeFlow Hermes Service",
    description="CLI驱动的FastAPI服务",
    version="2.5.0"
)


@app.post("/api/session/start", response_model=SessionResponse)
async def start_session(request: StartRequest):
    """启动CLI会话

    Args:
        request: 启动请求，包含prompt

    Returns:
        session_id和running状态

    Raises:
        HTTPException: 启动失败时返回500
    """
    try:
        process, session_id = driver.start_session(request.prompt)

        if not session_id:
            raise HTTPException(status_code=500, detail="无法获取session_id")

        return SessionResponse(session_id=session_id, status="running")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLI启动失败: {str(e)}")


@app.get("/api/session/{session_id}/events")
async def get_events(session_id: str):
    """获取事件流（SSE格式）

    Args:
        session_id: CLI会话ID

    Returns:
        SSE流：data: {...}\n\n

    Raises:
        HTTPException: session不存在返回404
    """
    session = driver.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    async def event_generator():
        """生成SSE事件流"""
        try:
            for event in driver.monitor_events(session.process):
                # 存储事件到session
                session.events.append(event)

                # SSE格式输出
                yield f"data: {json.dumps(event)}\n\n"

                # result事件表示完成，结束流
                if event.get("type") == "result":
                    break

        except Exception as e:
            # 发送错误事件
            error_event = {
                "type": "error",
                "message": str(e),
                "session_id": session_id
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.post("/api/session/{session_id}/intervene", response_model=SessionResponse)
async def intervene(session_id: str, request: InterveneRequest):
    """干预会话

    Args:
        session_id: CLI会话ID
        request: 干预请求，包含prompt

    Returns:
        session_id和intervened状态

    Raises:
        HTTPException: session不存在返回404，干预失败返回500
    """
    session = driver.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    try:
        new_process = driver.intervene(session_id, request.prompt)
        return SessionResponse(session_id=session_id, status="intervened")

    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"干预失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLI干预失败: {str(e)}")


@app.post("/api/session/{session_id}/cancel", response_model=SessionResponse)
async def cancel(session_id: str):
    """取消会话

    Args:
        session_id: CLI会话ID

    Returns:
        session_id和cancelled状态
    """
    # 无论session是否存在，都返回cancelled
    driver.clear_session(session_id)

    return SessionResponse(session_id=session_id, status="cancelled")


@app.get("/api/session/{session_id}/status", response_model=StatusResponse)
async def get_status(session_id: str):
    """查询会话状态

    Args:
        session_id: CLI会话ID

    Returns:
        session_id、status和events_count

    Raises:
        HTTPException: session不存在返回404
    """
    session = driver.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    # 判断进程状态
    is_alive = driver.is_process_alive(session_id)

    if is_alive:
        status = "running"
    else:
        # 检查是否有result事件
        events = session.events or []
        has_result = any(e.get("type") == "result" for e in events)
        status = "completed" if has_result else "terminated"

    return StatusResponse(
        session_id=session_id,
        status=status,
        events_count=len(session.events or [])
    )


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "healthy", "version": "2.5.0"}


# 启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)