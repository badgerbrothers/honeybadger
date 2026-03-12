"""Run API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, UTC
from app.database import get_db
from app.models.task import TaskRun, TaskStatus
from app.schemas.task import TaskRunResponse
from app.services.event_broadcaster import broadcaster

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/{run_id}", response_model=TaskRunResponse)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskRun).where(TaskRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/{run_id}/cancel", response_model=TaskRunResponse)
async def cancel_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskRun).where(TaskRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel run with status {run.status.value}")
    run.status = TaskStatus.CANCELLED
    run.completed_at = datetime.now(UTC).replace(tzinfo=None)  # Remove tzinfo for TIMESTAMP WITHOUT TIME ZONE
    await db.commit()
    await db.refresh(run)
    await broadcaster.broadcast(str(run_id), {"type": "status_change", "status": "cancelled"})
    return run


@router.websocket("/{run_id}/stream")
async def stream_events(websocket: WebSocket, run_id: uuid.UUID):
    run_id_str = str(run_id)
    await broadcaster.connect(run_id_str, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(run_id_str, websocket)
