"""Run API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, UTC
from app.database import get_db
from app.models.artifact import Artifact
from app.models.task import Task, TaskRun, TaskStatus
from app.schemas.artifact import ArtifactResponse
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
    task_result = await db.execute(select(Task).where(Task.id == run.task_id))
    task = task_result.scalar_one_or_none()
    if task and task.current_run_id == run.id:
        task.current_run_id = None
    await db.commit()
    await db.refresh(run)
    await broadcaster.broadcast(str(run_id), {"type": "status_change", "status": "cancelled"})
    return run


@router.post("/{run_id}/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_run_event(
    run_id: uuid.UUID,
    event: dict,
    db: AsyncSession = Depends(get_db),
):
    """Accept execution events from the worker and fan them out to subscribers."""
    result = await db.execute(select(TaskRun).where(TaskRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    logs = list(run.logs or [])
    logs.append(event)
    run.logs = logs
    await db.commit()
    await broadcaster.broadcast(str(run_id), event)
    return {"accepted": True}


@router.get("/{run_id}/artifacts", response_model=list[ArtifactResponse])
async def list_run_artifacts(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List artifacts produced by a run."""
    result = await db.execute(
        select(Artifact).where(Artifact.task_run_id == run_id).order_by(Artifact.created_at.desc())
    )
    return result.scalars().all()


@router.websocket("/{run_id}/stream")
async def stream_events(websocket: WebSocket, run_id: uuid.UUID):
    run_id_str = str(run_id)
    await broadcaster.connect(run_id_str, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(run_id_str, websocket)
