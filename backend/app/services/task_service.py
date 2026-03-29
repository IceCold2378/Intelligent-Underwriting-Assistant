"""
Background task manager for async execution and SSE streaming.

Tracks analysis tasks in the database and provides an event broker
for Server-Sent Events (SSE) so the frontend can display real-time progress.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.database import BackgroundTask
from app.models.schemas import TaskStatus, StreamEvent

logger = logging.getLogger(__name__)

# In-memory pub/sub broker for SSE
# Used to broadcast events from background workers to SSE clients
class EventBroker:
    def __init__(self):
        # dict[task_id: list[asyncio.Queue]]
        self._queues: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to events for a specific task."""
        if task_id not in self._queues:
            self._queues[task_id] = []
        q = asyncio.Queue()
        self._queues[task_id].append(q)
        return q

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from events."""
        if task_id in self._queues:
            self._queues[task_id].remove(queue)
            if not self._queues[task_id]:
                del self._queues[task_id]

    async def publish(self, task_id: str, event: StreamEvent) -> None:
        """Publish an event to all subscribers of a task."""
        if task_id in self._queues:
            for q in self._queues[task_id]:
                await q.put(event)


broker = EventBroker()


async def create_task(db: AsyncSession, user_id: int, task_type: str) -> str:
    """Create a new background task record."""
    task_id = f"task_{uuid.uuid4().hex}"
    
    db_task = BackgroundTask(
        id=task_id,
        user_id=user_id,
        task_type=task_type,
        status=TaskStatus.PENDING.value,
        progress=0.0,
    )
    
    db.add(db_task)
    await db.commit()
    return task_id


async def update_task_progress(
    db: AsyncSession, 
    task_id: str, 
    status: TaskStatus, 
    progress: float, 
    result: dict | None = None,
    trace: dict | None = None,
    error: str | None = None
) -> None:
    """Update task status in DB and broadcast to SSE listeners."""
    stmt = select(BackgroundTask).where(BackgroundTask.id == task_id)
    res = await db.execute(stmt)
    task = res.scalar_one_or_none()
    
    if not task:
        logger.warning("Task %s not found for update", task_id)
        return

    task.status = status.value
    task.progress = progress
    
    # Track the event to send
    event_type = status.value
    data = {"progress": progress}
    
    if result:
        task.result_json = result
        data["result"] = result
        
    if trace:
        task.agent_trace_json = trace
        data["trace"] = trace
        event_type = "agent_step"
        
    if error:
        task.error = error
        data["error"] = error
        event_type = "error"
        
    await db.commit()
    
    # Broadcast to SSE connected clients
    await broker.publish(
        task_id, 
        StreamEvent(event=event_type, data=data)
    )
    
    # If terminal state, wait briefly then dispatch a meta-event to close connections
    if status in (TaskStatus.COMPLETE, TaskStatus.FAILED):
        await asyncio.sleep(0.5)
        await broker.publish(task_id, StreamEvent(event="done", data={"task_id": task_id}))


async def run_analysis_task(
    db: AsyncSession,
    task_id: str,
    text: str,
    filename: str,
    analysis_func: Callable
) -> None:
    """
    Background worker that runs the analysis and updates progress.
    In a real system, this would be a Celery or ARQ worker.
    """
    try:
        # PENDING -> RUNNING
        await update_task_progress(db, task_id, TaskStatus.RUNNING, 10.0)
        
        # In a real streaming scenario, we'd pass a callback to the agent
        # For now, we simulate intermediate steps and then run the agent
        # This gives the UI a chance to render the streaming connection before the heavy LLM call
        
        await update_task_progress(db, task_id, TaskStatus.RUNNING, 20.0, 
            trace={"step": "extract_facts", "status": "running"})
            
        # Normally this would be a streamed LangGraph response
        result, trace = await analysis_func(text, filename)
        
        # COMPLETE
        await update_task_progress(
            db, 
            task_id, 
            TaskStatus.COMPLETE, 
            100.0, 
            result=result.model_dump(),
            trace=trace
        )
        
        # Trigger webhooks!
        try:
            from app.integrations.webhooks import webhook_manager, WebhookEvent
            # Fire and forget (WebhookManager handles its own async delivery)
            asyncio.create_task(webhook_manager.trigger(
                WebhookEvent.ANALYSIS_COMPLETE,
                result.model_dump()
            ))
        except Exception as e:
            logger.error("Failed to trigger webhook for task %s: %s", task_id, e)
            
    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        # FAILED
        await update_task_progress(db, task_id, TaskStatus.FAILED, 100.0, error=str(e))


async def sse_generator(task_id: str) -> AsyncGenerator[str, None]:
    """Generator for Server-Sent Events endpoint."""
    queue = broker.subscribe(task_id)
    try:
        # Send initial connection success
        yield f"event: connected\ndata: {json.dumps({'task_id': task_id})}\n\n"
        
        while True:
            # Wait for next event
            stream_event: StreamEvent = await queue.get()
            
            # Format as SSE string
            data_str = json.dumps(stream_event.data)
            yield f"event: {stream_event.event}\ndata: {data_str}\n\n"
            
            # Close connection if task is complete
            if stream_event.event == "done":
                break
    finally:
        broker.unsubscribe(task_id, queue)
