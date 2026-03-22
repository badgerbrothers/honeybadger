"""Tasks API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import structlog

from app.config import settings
from app.database import get_db
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.rag_collection import RagCollection
from app.models.task import QueueStatus, Task, TaskRun, TaskStatus
from app.schemas.model_catalog import ModelCatalogResponse
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse
from app.schemas.task_queue import TaskKanbanResponse
from app.security.auth import CurrentUser, get_current_user
from app.services.queue_service import queue_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = structlog.get_logger(__name__)


def _normalize_model(model: str) -> str:
    return model.strip().lower()


def _supported_model_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for model in settings.supported_models:
        lookup[_normalize_model(model)] = model
    return lookup


def _resolve_task_model(model: str | None) -> str:
    supported_models = _supported_model_lookup()
    default_key = _normalize_model(settings.default_main_model)

    if default_key not in supported_models:
        logger.error(
            "invalid_default_model_config",
            default_model=settings.default_main_model,
            supported_models=settings.supported_models,
        )
        raise HTTPException(status_code=500, detail="Task model configuration is invalid")

    if model is None or not model.strip():
        return supported_models[default_key]

    model_key = _normalize_model(model)
    if model_key not in supported_models:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Unsupported model: {model}",
                "supported_models": list(supported_models.values()),
            },
        )
    return supported_models[model_key]


async def _get_owned_task_or_404(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> Task:
    result = await db.execute(
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(
            Task.id == task_id,
            Project.owner_user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _ensure_owned_project_and_conversation(
    task: TaskCreate,
    user: CurrentUser,
    db: AsyncSession,
) -> Project:
    project_result = await db.execute(
        select(Project).where(
            Project.id == task.project_id,
            Project.owner_user_id == user.id,
        )
    )
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    conversation_result = await db.execute(
        select(Conversation).where(
            Conversation.id == task.conversation_id,
            Conversation.project_id == task.project_id,
        )
    )
    if conversation_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if task.rag_collection_id is not None:
        rag_result = await db.execute(
            select(RagCollection).where(
                RagCollection.id == task.rag_collection_id,
                RagCollection.owner_user_id == user.id,
            )
        )
        if rag_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="RAG collection not found")
    return project


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    conversation_id: uuid.UUID | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    queue_status: QueueStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    query = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Project.owner_user_id == user.id)
    )
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
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _ensure_owned_project_and_conversation(task=task, user=user, db=db)
    task_data = task.model_dump()
    if "rag_collection_id" not in task.model_fields_set:
        task_data["rag_collection_id"] = project.active_rag_collection_id
    task_data["model"] = _resolve_task_model(task.model)
    db_task = Task(**task_data)
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("/models", response_model=ModelCatalogResponse)
async def get_model_catalog():
    """Return default and supported models for task creation."""
    default_model = _resolve_task_model(None)
    return ModelCatalogResponse(
        default_model=default_model,
        supported_models=list(_supported_model_lookup().values()),
    )


@router.get("/kanban", response_model=TaskKanbanResponse)
async def get_kanban_board(
    project_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    query = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Project.owner_user_id == user.id)
    )
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
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
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
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)

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
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    await db.delete(task)
    await db.commit()


@router.get("/{task_id}/runs", response_model=list[TaskRunResponse])
async def list_task_runs(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    result = await db.execute(
        select(TaskRun).where(TaskRun.task_id == task_id).order_by(TaskRun.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{task_id}/runs", response_model=TaskRunResponse, status_code=201)
async def create_task_run(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
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
async def retry_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new run for an existing task."""
    return await create_task_run(task_id=task_id, db=db, user=user)
