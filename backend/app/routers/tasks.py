"""Tasks API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.database import get_db
from app.models.task import Task, TaskRun, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/", response_model=list[TaskResponse])
async def list_tasks(conversation_id: uuid.UUID | None = Query(None), project_id: uuid.UUID | None = Query(None), db: AsyncSession = Depends(get_db)):
    query = select(Task)
    if conversation_id:
        query = query.where(Task.conversation_id == conversation_id)
    if project_id:
        query = query.where(Task.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

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
    result = await db.execute(select(TaskRun).where(TaskRun.task_id == task_id))
    return result.scalars().all()

@router.post("/{task_id}/runs", response_model=TaskRunResponse, status_code=201)
async def create_task_run(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")
    db_run = TaskRun(task_id=task_id, status=TaskStatus.PENDING)
    db.add(db_run)
    await db.commit()
    await db.refresh(db_run)
    return db_run
