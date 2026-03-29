"""
Streaming router for Server-Sent Events (SSE).

Allows clients to subscribe to real-time progress updates for
background analysis tasks.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db
# Remove auth dependency to make streaming endpoint easily accessible from EventSource API
# The auth token should ideally be passed in GET parameters if strict auth is needed for SSE

from app.models.database import BackgroundTask
from app.services.task_service import sse_generator

router = APIRouter(prefix="/stream", tags=["Streaming"])


@router.get("/task/{task_id}")
async def stream_task_progress(
    request: Request,
    task_id: str,
    token: str | None = Query(None, description="Auth token for SSE connection"),
    db: AsyncSession = Depends(get_db),
):
    """
    Subscribe to real-time updates for a background task using Server-Sent Events.
    
    The client (e.g. browser EventSource) will receive updates for:
    - Task status changes
    - Agent trace steps (tool executions)
    - Final result or errors
    """
    # 1. We optionally check the token here (simplified auth for SSE)
    if token:
        from app.services.auth_service import decode_access_token
        try:
            decode_access_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")

    # 2. Check if task exists and is accessible
    stmt = select(BackgroundTask).where(BackgroundTask.id == task_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 3. Return the SSE streaming response
    return StreamingResponse(
        sse_generator(task_id),
        media_type="text/event-stream"
    )
