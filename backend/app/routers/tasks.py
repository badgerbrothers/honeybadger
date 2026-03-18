"""Tasks API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import structlog
from app.database import get_db
from app.models.task import Task, TaskRun, TaskStatus, QueueStatus
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse
from app.schemas.task_queue import TaskKanbanResponse
from app.services.queue_service import queue_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = structlog.get_logger(__name__)

@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    conversation_id: uuid.UUID | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    queue_status: QueueStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)
    if conversation_id:
        query = query.where(Task.conversation_id == conversation_id)
    if project_id:
        query = query.where(Task.project_id == project_id)
    if queue_status:
        query = query.where(Task.queue_status == queue_status)
    query = query.order_by(Task.priority.desc(), Task.scheduled_at.asc(), Task.created_at.asc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("/kanban", response_model=TaskKanbanResponse)
async def get_kanban_board(
    project_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)
    if project_id:
        query = query.where(Task.project_id == project_id)
    query = query.order_by(Task.priority.desc(), Task.scheduled_at.asc(), Task.created_at.asc())

    result = await db.execute(query)
    tasks = result.scalars().all()
    kanban = TaskKanbanResponse()
    for task in tasks:
        if task.queue_status == QueueStatus.SCHEDULED:
            kanban.scheduled.append(task)
        elif task.queue_status == QueueStatus.QUEUED:
            kanban.queued.append(task)
        elif task.queue_status == QueueStatus.IN_PROGRESS:
            kanban.in_progress.append(task)
        elif task.queue_status == QueueStatus.DONE:
            kanban.done.append(task)
    return kanban

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: uuid.UUID, task_update: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}/queue-status", response_model=TaskResponse)
async def update_task_queue_status(
    task_id: uuid.UUID,
    queue_status: QueueStatus = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.queue_status = queue_status
    publish_run_id: uuid.UUID | None = None

    if queue_status == QueueStatus.IN_PROGRESS and not task.current_run_id:
        db_run = TaskRun(task_id=task_id, status=TaskStatus.PENDING)
        db.add(db_run)
        await db.flush()
        task.current_run_id = db_run.id
        publish_run_id = db_run.id

    await db.commit()

    if publish_run_id is not None:
        try:
            await queue_service.publish_task_run(publish_run_id)
        except Exception as exc:
            logger.error(
                "task_queue_status_publish_failed",
                task_id=str(task_id),
                task_run_id=str(publish_run_id),
                error=str(exc),
                exc_info=True,
            )
            run_result = await db.execute(select(TaskRun).where(TaskRun.id == publish_run_id))
            db_run = run_result.scalar_one_or_none()
            if db_run:
                db_run.status = TaskStatus.FAILED
                db_run.error_message = "queue_publish_failed"
                task.current_run_id = None
                await db.commit()
            raise HTTPException(status_code=503, detail="Task run queue unavailable") from exc

    await db.refresh(task)
    logger.info("task_queue_status_updated", task_id=str(task_id), new_status=queue_status.value)
    return task

@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()

@router.get("/{task_id}/runs", response_model=list[TaskRunResponse])
async def list_task_runs(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")
    result = await db.execute(
        select(TaskRun).where(TaskRun.task_id == task_id).order_by(TaskRun.created_at.desc())
    )
    return result.scalars().all()

@router.post("/{task_id}/runs", response_model=TaskRunResponse, status_code=201)
async def create_task_run(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_run = TaskRun(task_id=task_id, status=TaskStatus.PENDING)
    db.add(db_run)
    await db.flush()
    task.current_run_id = db_run.id
    await db.commit()
    await db.refresh(db_run)
    try:
        await queue_service.publish_task_run(db_run.id)
    except Exception as exc:
        logger.error(
            "task_run_publish_failed",
            task_id=str(task_id),
            task_run_id=str(db_run.id),
            error=str(exc),
            exc_info=True,
        )
        db_run.status = TaskStatus.FAILED
        db_run.error_message = "queue_publish_failed"
        task.current_run_id = None
        await db.commit()
        await db.refresh(db_run)
        raise HTTPException(status_code=503, detail="Task run queue unavailable") from exc
    return db_run


@router.post("/{task_id}/retry", response_model=TaskRunResponse, status_code=201)
async def retry_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Create a new run for an existing task."""
    return await create_task_run(task_id=task_id, db=db)
