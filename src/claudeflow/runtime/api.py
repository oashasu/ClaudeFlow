"""Runtime API - FastAPI 服务入口

接管原 hermes_service.py 的全部 runtime + session 端点。
Python 服务直接管理多个 Claude Code CLI 进程。
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio
import os

from claudeflow.runtime.cli_driver import CliDriver
from claudeflow.runtime.manager import RuntimeManager, UnknownTaskError


# ── 请求/响应模型 ──────────────────────────────────────────


class StartRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="任务描述")


class InterveneRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="干预内容")


class RuntimeDispatchRequest(BaseModel):
    base_branch: str = Field(default="HEAD", description="基线分支")
    limit: Optional[int] = Field(default=None, ge=0, description="本次最多启动任务数")
    max_concurrent: Optional[int] = Field(default=None, ge=0, description="最大并发槽位")
    executor_type: str = Field(default="claude", description="执行器类型")


class RuntimeGovernanceDispatchRequest(BaseModel):
    governance_root: str = Field(..., min_length=1, description="治理任务包根目录")
    phase_id: str = Field(..., min_length=1, description="阶段 ID")
    base_branch: str = Field(default="HEAD", description="基线分支")
    limit: Optional[int] = Field(default=None, ge=0, description="本次最多启动任务数")


class RuntimeCompleteRequest(BaseModel):
    summary: str = Field(default="", description="完成摘要")
    changed_files: list[str] = Field(default_factory=list, description="变更文件")
    test_status: Optional[str] = Field(default=None, description="测试状态")
    test_count: Optional[int] = Field(default=None, ge=0, description="测试数量")


class RuntimeFailRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="失败原因")


class SessionResponse(BaseModel):
    session_id: str
    status: str


class StatusResponse(BaseModel):
    session_id: str
    status: str
    events_count: int = 0


# ── 全局实例 ───────────────────────────────────────────────

driver = CliDriver()
runtime_manager = RuntimeManager(
    repo_path=os.environ.get("CLAUDFLOW_REPO_DIR", os.getcwd()),
    driver=driver,
)

# ── FastAPI 应用 ───────────────────────────────────────────

app = FastAPI(
    title="ClaudeFlow Runtime API",
    description="Runtime + Session API，Python 服务直接管理多 CLI 进程",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://192.168.100.181:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Session 端点 ──────────────────────────────────────────


@app.post("/api/session/start", response_model=SessionResponse)
async def start_session(request: StartRequest):
    try:
        process, session_id = driver.start_session(request.prompt)
        if not session_id:
            raise HTTPException(status_code=500, detail="无法获取session_id")
        return SessionResponse(session_id=session_id, status="running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLI启动失败: {str(e)}")


@app.get("/api/session/{session_id}/events")
async def get_events(session_id: str):
    session = driver.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    async def event_generator():
        existing_events = list(session.events or [])
        for event in existing_events:
            yield f"data: {json.dumps(event)}\n\n"

        if not existing_events:
            for event in driver.monitor_events(session.process):
                session.events.append(event)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "result":
                    yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                    return

        last_count = len(session.events or [])
        while driver.is_process_alive(session_id):
            await asyncio.sleep(1)
            current_events = session.events or []
            for event in current_events[last_count:]:
                yield f"data: {json.dumps(event)}\n\n"
            last_count = len(current_events)

        yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/session/{session_id}/intervene", response_model=SessionResponse)
async def intervene(session_id: str, request: InterveneRequest):
    session = driver.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")
    try:
        driver.intervene(session_id, request.prompt)
        return SessionResponse(session_id=session_id, status="intervened")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"干预失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CLI干预失败: {str(e)}")


@app.post("/api/session/{session_id}/cancel", response_model=SessionResponse)
async def cancel(session_id: str):
    driver.clear_session(session_id)
    return SessionResponse(session_id=session_id, status="cancelled")


@app.get("/api/session/{session_id}/status", response_model=StatusResponse)
async def get_status(session_id: str):
    session = driver.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    is_alive = driver.is_process_alive(session_id)
    if is_alive:
        status = "running"
    else:
        events = session.events or []
        has_result = any(e.get("type") == "result" for e in events)
        status = "completed" if has_result else "terminated"

    return StatusResponse(
        session_id=session_id,
        status=status,
        events_count=len(session.events or []),
    )


@app.get("/api/session/{session_id}/events-list")
async def get_events_list(session_id: str):
    session = driver.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session不存在")

    parsed_events = []
    for event in (session.events or []):
        parsed = driver.parse_all_assistant_content(event)
        if parsed:
            parsed_events.extend(parsed)

    return {
        "session_id": session_id,
        "events_count": len(session.events or []),
        "parsed_events": parsed_events,
        "raw_events": session.events or [],
    }


# ── Runtime 端点 ──────────────────────────────────────────


@app.get("/api/runtime/plan")
async def get_runtime_plan(executor_type: str = "claude"):
    """T106: 获取调度计划，输出包含 executor_type。"""
    plan = runtime_manager.get_dispatch_plan(executor_type=executor_type)
    return {
        "runnable": [
            {
                "task_id": task.task_id,
                "priority": task.priority,
                "executor_type": task.executor_type,  # T106: 宿主字段
                "phase_id": task.phase_id,  # T109: RuntimeTaskSpec 字段
            }
            for task in plan["runnable"]
        ],
        "blocked": plan["blocked"],
        "running": plan["running"],
    }


@app.get("/api/runtime/status")
async def get_runtime_status():
    return runtime_manager.get_runtime_status()


@app.get("/api/runtime/sessions")
async def list_runtime_sessions():
    return {"sessions": runtime_manager.list_session_indexes()}


@app.get("/api/runtime/explain/{task_id}")
async def explain_runtime_task(task_id: str):
    try:
        return runtime_manager.explain_task(task_id)
    except UnknownTaskError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/runtime/dispatch")
async def dispatch_runtime(request: RuntimeDispatchRequest):
    """T106: 派发任务，支持 executor_type 参数。"""
    return runtime_manager.dispatch_runnable_tasks(
        base_branch=request.base_branch,
        limit=request.limit,
        max_concurrent=request.max_concurrent,
        executor_type=request.executor_type,
    )


@app.post("/api/runtime/dispatch/governance")
async def dispatch_runtime_governance(request: RuntimeGovernanceDispatchRequest):
    """T106: 从治理任务包派发任务。"""
    return runtime_manager.dispatch_from_governance(
        governance_root=request.governance_root,
        phase_id=request.phase_id,
        base_branch=request.base_branch,
        limit=request.limit,
    )


@app.post("/api/runtime/task/{task_id}/complete")
async def complete_runtime_task(task_id: str, request: RuntimeCompleteRequest):
    try:
        tests = {}
        if request.test_status is not None:
            tests["status"] = request.test_status
        if request.test_count is not None:
            tests["count"] = request.test_count
        return runtime_manager.complete_worker(
            task_id,
            summary=request.summary,
            changed_files=request.changed_files,
            tests=tests or None,
        )
    except UnknownTaskError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/runtime/task/{task_id}/fail")
async def fail_runtime_task(task_id: str, request: RuntimeFailRequest):
    try:
        return runtime_manager.fail_worker(task_id, request.reason)
    except UnknownTaskError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Health ────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
