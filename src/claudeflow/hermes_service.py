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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio
import os

from claudeflow.cli_driver import CliDriver
from claudeflow.runtime import RuntimeManager, UnknownTaskError


# 请求模型
class StartRequest(BaseModel):
    """启动会话请求"""
    prompt: str = Field(..., min_length=1, description="任务描述")


class InterveneRequest(BaseModel):
    """干预会话请求"""
    prompt: str = Field(..., min_length=1, description="干预内容")


class RuntimeDispatchRequest(BaseModel):
    """运行时调度请求。"""

    base_branch: str = Field(default="HEAD", description="基线分支")
    limit: Optional[int] = Field(default=None, ge=0, description="本次最多启动任务数")
    max_concurrent: Optional[int] = Field(default=None, ge=0, description="最大并发槽位")


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
runtime_manager = RuntimeManager(
    repo_path=os.environ.get("CLAUDFLOW_REPO_DIR", os.getcwd()),
    driver=driver,
)

# FastAPI应用
app = FastAPI(
    title="ClaudeFlow Hermes Service",
    description="CLI驱动的FastAPI服务",
    version="2.5.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://192.168.100.181:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """获取事件流（SSE格式）- 从已存储的事件读取

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
        """生成SSE事件流 - 从已存储的事件读取"""
        existing_events = list(session.events or [])

        # 先发送已存储的事件
        for event in existing_events:
            yield f"data: {json.dumps(event)}\n\n"

        # 兼容旧模式：如果当前还没有缓存事件，则直接读取monitor_events
        if not existing_events:
            for event in driver.monitor_events(session.process):
                session.events.append(event)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "result":
                    yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                    return

        # 如果进程还在运行，等待新事件
        last_count = len(session.events or [])
        while driver.is_process_alive(session_id):
            await asyncio.sleep(1)
            current_events = session.events or []
            # 发送新增的事件
            for event in current_events[last_count:]:
                yield f"data: {json.dumps(event)}\n\n"
            last_count = len(current_events)

        # 发送完成标记
        yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"

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


@app.get("/api/session/{session_id}/events-list")
async def get_events_list(session_id: str):
    """获取会话事件列表

    Args:
        session_id: CLI会话ID

    Returns:
        事件列表

    Raises:
        HTTPException: session不存在返回404
    """
    session = driver.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    # 解析assistant事件，提取关键信息
    parsed_events = []
    for event in (session.events or []):
        parsed = driver.parse_all_assistant_content(event)
        if parsed:
            parsed_events.extend(parsed)

    return {
        "session_id": session_id,
        "events_count": len(session.events or []),
        "parsed_events": parsed_events,
        "raw_events": session.events or []
    }


@app.get("/api/runtime/plan")
async def get_runtime_plan():
    """获取当前 runtime 调度计划。"""
    plan = runtime_manager.get_dispatch_plan()
    return {
        "runnable": [
            {
                "task_id": task.task_id,
                "priority": task.priority,
                "owner_role": task.owner_role,
                "task_type": task.task_type,
            }
            for task in plan["runnable"]
        ],
        "blocked": plan["blocked"],
        "running": plan["running"],
    }


@app.get("/api/runtime/status")
async def get_runtime_status():
    """获取 runtime 总览状态。"""
    return runtime_manager.get_runtime_status()


@app.get("/api/runtime/sessions")
async def list_runtime_sessions():
    """获取 runtime session 索引列表。"""
    return {
        "sessions": runtime_manager.list_session_indexes(),
    }


@app.get("/api/runtime/explain/{task_id}")
async def explain_runtime_task(task_id: str):
    """解释单个任务当前运行状态。"""
    try:
        return runtime_manager.explain_task(task_id)
    except UnknownTaskError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/runtime/dispatch")
async def dispatch_runtime(request: RuntimeDispatchRequest):
    """执行一次 runtime dispatch。"""
    return runtime_manager.dispatch_runnable_tasks(
        base_branch=request.base_branch,
        limit=request.limit,
        max_concurrent=request.max_concurrent,
    )


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "healthy", "version": "2.5.0"}


# 启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
