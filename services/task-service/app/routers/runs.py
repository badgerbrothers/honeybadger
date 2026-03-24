"""Run API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, UTC
import structlog
from app.database import async_session_maker, get_db
from app.models.artifact import Artifact
from app.models.project import Project
from app.models.task import Task, TaskRun, TaskStatus
from app.schemas.artifact import ArtifactResponse
from app.schemas.task import TaskRunResponse
from app.security.auth import (
    CurrentUser,
    decode_access_token,
    get_current_user,
    require_internal_service_token,
)
from app.services.event_broadcaster import broadcaster
from app.services.task_retry_service import task_retry_service

router = APIRouter(prefix="/api/runs", tags=["runs"])
logger = structlog.get_logger(__name__)


async def _get_owned_run_or_404(
    run_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> TaskRun:
    result = await db.execute(
        select(TaskRun)
        .join(Task, TaskRun.task_id == Task.id)
        .join(Project, Task.project_id == Project.id)
        .where(
            TaskRun.id == run_id,
            Project.owner_user_id == user.id,
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}", response_model=TaskRunResponse)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _get_owned_run_or_404(run_id=run_id, user=user, db=db)
    return run


@router.post("/{run_id}/cancel", response_model=TaskRunResponse)
async def cancel_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    run = await _get_owned_run_or_404(run_id=run_id, user=user, db=db)
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
    _: None = Depends(require_internal_service_token),
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

    if event.get("type") == "run_failed":
        task_result = await db.execute(select(Task).where(Task.id == run.task_id))
        task = task_result.scalar_one_or_none()
        if task is not None:
            try:
                await task_retry_service.maybe_schedule_retry(
                    db=db,
                    run=run,
                    task=task,
                    event=event,
                )
            except Exception as exc:
                logger.error(
                    "task_retry_evaluation_failed",
                    run_id=str(run_id),
                    task_id=str(run.task_id),
                    error=str(exc),
                    exc_info=True,
                )

    await broadcaster.broadcast(str(run_id), event)
    return {"accepted": True}


@router.get("/{run_id}/artifacts", response_model=list[ArtifactResponse])
async def list_run_artifacts(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """List artifacts produced by a run."""
    await _get_owned_run_or_404(run_id=run_id, user=user, db=db)
    result = await db.execute(
        select(Artifact).where(Artifact.task_run_id == run_id).order_by(Artifact.created_at.desc())
    )
    return result.scalars().all()


@router.websocket("/{run_id}/stream")
async def stream_events(websocket: WebSocket, run_id: uuid.UUID):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        user = decode_access_token(token)
    except HTTPException:
        await websocket.close(code=4401)
        return
    async with async_session_maker() as session:
        try:
            await _get_owned_run_or_404(run_id=run_id, user=user, db=session)
        except HTTPException:
            await websocket.close(code=4404)
            return
    run_id_str = str(run_id)
    await broadcaster.connect(run_id_str, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(run_id_str, websocket)
