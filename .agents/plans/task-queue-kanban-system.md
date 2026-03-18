# Feature: Task Queue Kanban Management System

将任务管理升级为看板式队列系统，支持任务状态流转、定时调度、优先级管理和多Agent协作。

## Feature Description

实现一个类似Kanban看板的任务队列管理系统，允许用户可视化管理多个任务的生命周期。任务可以处于4个状态（Scheduled/Queue/In Progress/Done），支持定时调度、优先级排序、Agent分配和拖拽操作。系统自动将到期的Scheduled任务移到Queue，Worker从Queue中取任务执行。

## User Story

As a user managing multiple AI tasks
I want to see all tasks in a Kanban board with different status columns
So that I can visualize task progress, schedule future tasks, and manage execution priorities

## Problem Statement

当前系统存在以下问题：
1. **缺少任务调度**：无法设置任务的计划执行时间，只能立即执行
2. **缺少状态可视化**：无法直观看到哪些任务在等待、执行中、已完成
3. **缺少优先级管理**：无法控制多个任务的执行顺序
4. **缺少Agent分配**：无法指定特定Agent执行特定任务
5. **缺少批量管理**：无法一次性管理多个任务的状态

## Solution Statement

扩展Task模型，添加调度和队列管理功能：
1. 添加`scheduled_at`字段支持定时任务
2. 添加`queue_status`字段管理任务在队列中的状态
3. 添加`priority`字段控制执行顺序
4. 添加`assigned_agent`字段分配执行者
5. 实现Scheduler服务，定时将到期任务移到Queue
6. 实现Frontend看板UI，支持拖拽和状态流转
7. 与现有RabbitMQ队列集成

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium-High
**Primary Systems Affected**:
- Backend Task模型和API
- Database Schema (tasks表)
- Scheduler服务（新增）
- Frontend看板UI（新增）
- RabbitMQ队列集成

**Dependencies**:
- RabbitMQ (已有)
- APScheduler 3.10+ (定时任务调度)
- React DnD 16+ (拖拽功能)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Backend - Task模型和API**:
- `backend/app/models/task.py` (lines 10-33) - 当前Task和TaskRun模型定义
- `backend/app/schemas/task.py` (lines 7-46) - Task的Pydantic schemas
- `backend/app/routers/tasks.py` (lines 15-107) - Task CRUD API端点
- `backend/app/routers/runs.py` (lines 17-84) - TaskRun管理API

**Backend - 队列服务**:
- `backend/app/services/queue_service.py` (lines 1-153) - RabbitMQ发布服务
- `backend/app/main.py` (lines 10-19) - FastAPI启动和关闭事件

**Worker**:
- `worker/worker_taskrun.py` (lines 510-540) - TaskRun Worker消费逻辑
- `worker/main.py` (lines 89-127) - Worker执行函数

**Frontend**:
- `frontend/src/features/tasks/api/tasks.ts` - Task API客户端
- `frontend/src/features/tasks/components/TaskStatusBadge.tsx` - 状态徽章组件
- `frontend/src/lib/types.ts` - TypeScript类型定义

**Database**:
- `backend/alembic/versions/1004c8374fe5_initial_schema_with_all_models.py` (lines 60-74) - tasks表结构

### New Files to Create

**Backend**:
- `backend/app/services/task_scheduler.py` - 任务调度服务
- `backend/app/schemas/task_queue.py` - 队列相关schemas
- `backend/alembic/versions/006_task_queue_fields.py` - 数据库迁移

**Frontend**:
- `frontend/src/features/tasks/components/TaskKanbanBoard.tsx` - 看板主组件
- `frontend/src/features/tasks/components/TaskCard.tsx` - 任务卡片组件
- `frontend/src/features/tasks/components/KanbanColumn.tsx` - 看板列组件
- `frontend/src/features/tasks/hooks/useTaskKanban.ts` - 看板数据管理Hook
- `frontend/src/app/tasks/kanban/page.tsx` - 看板页面

**Tests**:
- `backend/tests/test_task_scheduler.py` - 调度器测试
- `frontend/src/features/tasks/components/__tests__/TaskKanbanBoard.test.tsx` - 看板组件测试

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/3.x/)
  - Specific section: AsyncIOScheduler
  - Why: 用于实现定时任务调度器
- [React DnD Documentation](https://react-dnd.github.io/react-dnd/docs/overview)
  - Specific section: Hooks API
  - Why: 实现看板拖拽功能
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - Specific section: AsyncSession
  - Why: 调度器中的异步数据库操作

### Patterns to Follow

**Enum Pattern** (from `backend/app/models/task.py:10-15`):
```python
class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

**Model Pattern** (from `backend/app/models/task.py:17-33`):
```python
class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # ... fields
```

**Schema Pattern** (from `backend/app/schemas/task.py:7-14`):
```python
class TaskCreate(BaseModel):
    """Schema for creating a task."""
    conversation_id: uuid.UUID
    project_id: uuid.UUID
    goal: str = Field(..., min_length=1)
```

**Router Pattern** (from `backend/app/routers/tasks.py:25-31`):
```python
@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task
```

**Logging Pattern** (from `backend/app/routers/tasks.py:13`):
```python
import structlog
logger = structlog.get_logger(__name__)
logger.info("event_name", key=value)
```

**Frontend Hook Pattern** (from `frontend/src/features/tasks/hooks/useTasks.ts`):
```typescript
export function useTasks(params?: { conversationId?: string; projectId?: string }) {
  return useQuery({
    queryKey: ['tasks', params],
    queryFn: () => fetchTasks(params),
  });
}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Database Schema Extension

扩展Task模型，添加队列管理所需字段。

**Tasks:**
- 添加`queue_status`枚举字段（scheduled/queued/in_progress/done）
- 添加`scheduled_at`时间字段
- 添加`priority`优先级字段
- 添加`assigned_agent`字段
- 创建数据库迁移脚本

### Phase 2: Backend API Enhancement

扩展Task API，支持队列状态管理和批量操作。

**Tasks:**
- 更新Task schemas支持新字段
- 添加队列状态转换API
- 添加批量查询API（按状态分组）
- 添加优先级排序逻辑

### Phase 3: Task Scheduler Service

实现定时调度器，自动将到期任务移到Queue。

**Tasks:**
- 创建TaskScheduler服务
- 集成APScheduler
- 实现scheduled → queued转换逻辑
- 与RabbitMQ集成

### Phase 4: Frontend Kanban UI

实现看板界面，支持拖拽和状态流转。

**Tasks:**
- 创建看板布局组件
- 实现4列看板（Scheduled/Queue/In Progress/Done）
- 集成React DnD拖拽
- 实现任务卡片组件
- 添加实时更新

### Phase 5: Integration & Testing

集成所有组件，进行端到端测试。

**Tasks:**
- 集成Scheduler到Backend启动流程
- 测试完整工作流
- 添加单元测试和集成测试
- 性能优化

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Phase 1: Database Schema Extension

### Task 1.1: CREATE backend/app/models/task.py - Add QueueStatus enum

- **ADD**: QueueStatus枚举类
- **PATTERN**: 复用TaskStatus枚举模式 (task.py:10-15)
- **IMPLEMENTATION**:
  ```python
  class QueueStatus(enum.Enum):
      SCHEDULED = "scheduled"
      QUEUED = "queued"
      IN_PROGRESS = "in_progress"
      DONE = "done"
  ```
- **GOTCHA**: 放在TaskStatus枚举之后
- **VALIDATE**: `cd backend && uv run python -c "from app.models.task import QueueStatus; print(QueueStatus.SCHEDULED)"`

### Task 1.2: UPDATE backend/app/models/task.py - Add queue fields to Task model

- **ADD**: 4个新字段到Task模型
- **PATTERN**: 遵循现有字段定义模式 (task.py:20-27)
- **IMPLEMENTATION**:
  ```python
  queue_status: Mapped[QueueStatus] = mapped_column(SQLEnum(QueueStatus), nullable=False, default=QueueStatus.SCHEDULED, index=True)
  scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
  priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
  assigned_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
  ```
- **IMPORTS**: `from sqlalchemy import Integer`
- **GOTCHA**: 添加index=True以优化查询性能
- **VALIDATE**: `cd backend && uv run python -c "from app.models.task import Task; print(Task.__table__.columns.keys())"`


### Task 1.3: CREATE backend/alembic/versions/006_task_queue_fields.py

- **CREATE**: 数据库迁移脚本
- **PATTERN**: 复用现有迁移脚本结构 (1004c8374fe5_initial_schema_with_all_models.py)
- **IMPLEMENTATION**:
  ```python
  """Add task queue management fields

  Revision ID: 006
  Revises: 1005
  Create Date: 2026-03-17
  """
  from alembic import op
  import sqlalchemy as sa

  revision = '006'
  down_revision = '1005'

  def upgrade() -> None:
      op.add_column('tasks', sa.Column('queue_status', sa.Enum('SCHEDULED', 'QUEUED', 'IN_PROGRESS', 'DONE', name='queuestatus'), nullable=False, server_default='SCHEDULED'))
      op.add_column('tasks', sa.Column('scheduled_at', sa.DateTime(), nullable=True))
      op.add_column('tasks', sa.Column('priority', sa.Integer(), nullable=False, server_default='0'))
      op.add_column('tasks', sa.Column('assigned_agent', sa.String(100), nullable=True))
      op.create_index('ix_tasks_queue_status', 'tasks', ['queue_status'])
      op.create_index('ix_tasks_scheduled_at', 'tasks', ['scheduled_at'])
      op.create_index('ix_tasks_priority', 'tasks', ['priority'])

  def downgrade() -> None:
      op.drop_index('ix_tasks_priority', 'tasks')
      op.drop_index('ix_tasks_scheduled_at', 'tasks')
      op.drop_index('ix_tasks_queue_status', 'tasks')
      op.drop_column('tasks', 'assigned_agent')
      op.drop_column('tasks', 'priority')
      op.drop_column('tasks', 'scheduled_at')
      op.drop_column('tasks', 'queue_status')
  ```
- **VALIDATE**: `cd backend && uv run alembic upgrade head`

### Task 1.4: UPDATE backend/app/schemas/task.py - Add queue fields to schemas

- **UPDATE**: TaskCreate和TaskResponse schemas
- **PATTERN**: 遵循现有schema模式 (task.py:7-32)
- **IMPORTS**: `from app.models.task import QueueStatus`
- **IMPLEMENTATION**:
  ```python
  # 在TaskCreate中添加
  scheduled_at: datetime | None = None
  priority: int = Field(default=0, ge=0, le=100)
  assigned_agent: str | None = Field(None, max_length=100)
  
  # 在TaskResponse中添加
  queue_status: QueueStatus
  scheduled_at: datetime | None
  priority: int
  assigned_agent: str | None
  ```
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas.task import TaskCreate, TaskResponse; print('OK')"`

### Phase 2: Backend API Enhancement

### Task 2.1: UPDATE backend/app/routers/tasks.py - Add queue status filter

- **ADD**: 新的查询参数支持按queue_status过滤
- **PATTERN**: 复用现有过滤逻辑 (tasks.py:16-23)
- **IMPLEMENTATION**:
  ```python
  @router.get("/", response_model=list[TaskResponse])
  async def list_tasks(
      conversation_id: uuid.UUID | None = Query(None),
      project_id: uuid.UUID | None = Query(None),
      queue_status: QueueStatus | None = Query(None),
      db: AsyncSession = Depends(get_db)
  ):
      query = select(Task)
      if conversation_id:
          query = query.where(Task.conversation_id == conversation_id)
      if project_id:
          query = query.where(Task.project_id == project_id)
      if queue_status:
          query = query.where(Task.queue_status == queue_status)
      query = query.order_by(Task.priority.desc(), Task.scheduled_at.asc())
      result = await db.execute(query)
      return result.scalars().all()
  ```
- **IMPORTS**: `from app.models.task import QueueStatus`
- **VALIDATE**: `cd backend && uv run python -c "from app.routers.tasks import router; print('OK')"`


### Task 2.2: ADD backend/app/routers/tasks.py - Add queue status transition endpoint

- **ADD**: 新端点用于改变任务队列状态
- **PATTERN**: 复用update_task模式 (tasks.py:41-51)
- **IMPLEMENTATION**:
  ```python
  @router.patch("/{task_id}/queue-status", response_model=TaskResponse)
  async def update_task_queue_status(
      task_id: uuid.UUID,
      queue_status: QueueStatus,
      db: AsyncSession = Depends(get_db)
  ):
      result = await db.execute(select(Task).where(Task.id == task_id))
      task = result.scalar_one_or_none()
      if not task:
          raise HTTPException(status_code=404, detail="Task not found")
      
      task.queue_status = queue_status
      if queue_status == QueueStatus.IN_PROGRESS and not task.current_run_id:
          # 自动创建TaskRun
          db_run = TaskRun(task_id=task_id, status=TaskStatus.PENDING)
          db.add(db_run)
          await db.flush()
          task.current_run_id = db_run.id
          await queue_service.publish_task_run(db_run.id)
      
      await db.commit()
      await db.refresh(task)
      logger.info("task_queue_status_updated", task_id=str(task_id), new_status=queue_status.value)
      return task
  ```
- **VALIDATE**: `cd backend && uv run python -c "from app.routers.tasks import router; print('OK')"`

### Task 2.3: ADD backend/app/routers/tasks.py - Add kanban board data endpoint

- **ADD**: 返回按状态分组的任务数据
- **IMPLEMENTATION**:
  ```python
  @router.get("/kanban", response_model=dict)
  async def get_kanban_board(
      project_id: uuid.UUID | None = Query(None),
      db: AsyncSession = Depends(get_db)
  ):
      query = select(Task)
      if project_id:
          query = query.where(Task.project_id == project_id)
      
      result = await db.execute(query.order_by(Task.priority.desc(), Task.scheduled_at.asc()))
      tasks = result.scalars().all()
      
      kanban = {
          "scheduled": [],
          "queued": [],
          "in_progress": [],
          "done": []
      }
      
      for task in tasks:
          status_key = task.queue_status.value
          kanban[status_key].append(task)
      
      return kanban
  ```
- **VALIDATE**: `cd backend && uv run python -c "from app.routers.tasks import router; print('OK')"`

### Phase 3: Task Scheduler Service

### Task 3.1: UPDATE backend/pyproject.toml - Add APScheduler dependency

- **ADD**: APScheduler到依赖列表
- **PATTERN**: 遵循现有依赖格式 (pyproject.toml)
- **IMPLEMENTATION**: 添加 `"apscheduler>=3.10.0",` 到dependencies
- **VALIDATE**: `cd backend && uv sync && uv run python -c "import apscheduler; print(apscheduler.__version__)"`


### Task 3.2: CREATE backend/app/services/task_scheduler.py

- **CREATE**: 任务调度服务
- **PATTERN**: 复用queue_service结构 (queue_service.py)
- **IMPORTS**: `import asyncio, structlog, from apscheduler.schedulers.asyncio import AsyncIOScheduler, from datetime import datetime, UTC`
- **IMPLEMENTATION**:
  ```python
  """Task scheduler for moving scheduled tasks to queue."""
  import asyncio
  import structlog
  from datetime import datetime, UTC
  from apscheduler.schedulers.asyncio import AsyncIOScheduler
  from sqlalchemy import select
  from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
  from app.models.task import Task, QueueStatus
  from app.database import async_session_maker
  from app.services.queue_service import queue_service

  logger = structlog.get_logger(__name__)

  class TaskScheduler:
      """Scheduler for automatic task queue management."""
      
      def __init__(self):
          self.scheduler = AsyncIOScheduler()
          self.running = False
      
      async def start(self):
          """Start the scheduler."""
          if self.running:
              return
          self.scheduler.add_job(
              self._process_scheduled_tasks,
              'interval',
              seconds=30,
              id='process_scheduled_tasks'
          )
          self.scheduler.start()
          self.running = True
          logger.info("task_scheduler_started")
      
      async def stop(self):
          """Stop the scheduler."""
          if not self.running:
              return
          self.scheduler.shutdown()
          self.running = False
          logger.info("task_scheduler_stopped")
      
      async def _process_scheduled_tasks(self):
          """Move due scheduled tasks to queue."""
          async with async_session_maker() as session:
              now = datetime.now(UTC).replace(tzinfo=None)
              result = await session.execute(
                  select(Task).where(
                      Task.queue_status == QueueStatus.SCHEDULED,
                      Task.scheduled_at <= now
                  )
              )
              tasks = result.scalars().all()
              
              for task in tasks:
                  task.queue_status = QueueStatus.QUEUED
                  logger.info("task_moved_to_queue", task_id=str(task.id))
              
              await session.commit()
              
              if tasks:
                  logger.info("scheduled_tasks_processed", count=len(tasks))

  task_scheduler = TaskScheduler()
  ```
- **VALIDATE**: `cd backend && uv run python -c "from app.services.task_scheduler import task_scheduler; print('OK')"`

### Task 3.3: UPDATE backend/app/main.py - Integrate scheduler

- **ADD**: 启动和关闭scheduler
- **PATTERN**: 复用queue_service集成模式 (main.py:10-19)
- **IMPORTS**: `from app.services.task_scheduler import task_scheduler`
- **IMPLEMENTATION**:
  ```python
  @app.on_event("startup")
  async def startup_event():
      await queue_service.connect()
      await task_scheduler.start()

  @app.on_event("shutdown")
  async def shutdown_event():
      await task_scheduler.stop()
      await queue_service.close()
  ```
- **VALIDATE**: `cd backend && uv run python -c "from app.main import app; print('OK')"`


### Phase 4: Frontend Kanban UI

### Task 4.1: UPDATE frontend/package.json - Add React DnD dependencies

- **ADD**: React DnD库
- **IMPLEMENTATION**: 添加 `"react-dnd": "^16.0.1"` 和 `"react-dnd-html5-backend": "^16.0.1"`
- **VALIDATE**: `cd frontend && npm install && npm list react-dnd`

### Task 4.2: UPDATE frontend/src/lib/types.ts - Add queue types

- **ADD**: QueueStatus类型定义
- **PATTERN**: 复用TaskStatus模式
- **IMPLEMENTATION**:
  ```typescript
  export type QueueStatus = 'scheduled' | 'queued' | 'in_progress' | 'done';
  
  export interface Task {
    id: string;
    conversation_id: string;
    project_id: string;
    goal: string;
    skill: string | null;
    model: string;
    current_run_id: string | null;
    queue_status: QueueStatus;
    scheduled_at: string | null;
    priority: number;
    assigned_agent: string | null;
    created_at: string;
    updated_at: string;
  }
  ```
- **VALIDATE**: `cd frontend && npm run build`

### Task 4.3: CREATE frontend/src/features/tasks/api/kanban.ts

- **CREATE**: Kanban API客户端
- **PATTERN**: 复用tasks.ts模式
- **IMPLEMENTATION**:
  ```typescript
  import { request } from '@/lib/api';
  import { Task, QueueStatus } from '@/lib/types';

  export async function fetchKanbanBoard(projectId?: string): Promise<{
    scheduled: Task[];
    queued: Task[];
    in_progress: Task[];
    done: Task[];
  }> {
    const query = projectId ? `?project_id=${projectId}` : '';
    return request(`/tasks/kanban${query}`);
  }

  export async function updateTaskQueueStatus(
    taskId: string,
    queueStatus: QueueStatus
  ): Promise<Task> {
    return request(`/tasks/${taskId}/queue-status?queue_status=${queueStatus}`, {
      method: 'PATCH',
    });
  }
  ```
- **VALIDATE**: `cd frontend && npm run build`

### Task 4.4: CREATE frontend/src/features/tasks/components/TaskCard.tsx

- **CREATE**: 任务卡片组件
- **PATTERN**: 复用Card组件样式
- **IMPLEMENTATION**:
  ```typescript
  'use client';
  
  import { Task } from '@/lib/types';
  import { Card } from '@/components/ui/Card';
  
  interface TaskCardProps {
    task: Task;
  }
  
  export function TaskCard({ task }: TaskCardProps) {
    return (
      <Card className="p-4 mb-2 cursor-move hover:shadow-md transition-shadow">
        <h3 className="font-medium text-sm mb-2">{task.goal}</h3>
        <div className="flex items-center gap-2 text-xs text-gray-600">
          {task.assigned_agent && (
            <span className="flex items-center gap-1">
              <span>👤</span>
              <span>{task.assigned_agent}</span>
            </span>
          )}
          {task.scheduled_at && (
            <span className="flex items-center gap-1">
              <span>📅</span>
              <span>{new Date(task.scheduled_at).toLocaleString()}</span>
            </span>
          )}
          {task.priority > 0 && (
            <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded">
              P{task.priority}
            </span>
          )}
        </div>
      </Card>
    );
  }
  ```
- **VALIDATE**: `cd frontend && npm run build`


### Task 4.5: CREATE frontend/src/features/tasks/components/KanbanColumn.tsx

- **CREATE**: 看板列组件
- **PATTERN**: 使用React DnD的useDrop hook
- **IMPLEMENTATION**:
  ```typescript
  'use client';
  
  import { QueueStatus, Task } from '@/lib/types';
  import { TaskCard } from './TaskCard';
  
  interface KanbanColumnProps {
    title: string;
    status: QueueStatus;
    tasks: Task[];
    count: number;
    onDrop: (taskId: string, newStatus: QueueStatus) => void;
  }
  
  export function KanbanColumn({ title, status, tasks, count, onDrop }: KanbanColumnProps) {
    return (
      <div className="flex-1 min-w-[280px] bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-700">{title}</h2>
          <span className="px-2 py-1 bg-gray-200 text-gray-600 rounded-full text-sm">
            {count}
          </span>
        </div>
        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
          {tasks.length === 0 && (
            <p className="text-center text-gray-400 py-8">No tasks</p>
          )}
        </div>
      </div>
    );
  }
  ```
- **VALIDATE**: `cd frontend && npm run build`

### Task 4.6: CREATE frontend/src/features/tasks/hooks/useTaskKanban.ts

- **CREATE**: Kanban数据管理Hook
- **PATTERN**: 复用useQuery模式
- **IMPLEMENTATION**:
  ```typescript
  import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
  import { fetchKanbanBoard, updateTaskQueueStatus } from '../api/kanban';
  import { QueueStatus } from '@/lib/types';
  
  export function useTaskKanban(projectId?: string) {
    const queryClient = useQueryClient();
    
    const { data, isLoading, error } = useQuery({
      queryKey: ['kanban', projectId],
      queryFn: () => fetchKanbanBoard(projectId),
      refetchInterval: 5000, // 每5秒刷新
    });
    
    const updateStatus = useMutation({
      mutationFn: ({ taskId, status }: { taskId: string; status: QueueStatus }) =>
        updateTaskQueueStatus(taskId, status),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['kanban', projectId] });
      },
    });
    
    return {
      kanban: data,
      isLoading,
      error,
      updateTaskStatus: updateStatus.mutate,
    };
  }
  ```
- **VALIDATE**: `cd frontend && npm run build`

### Task 4.7: CREATE frontend/src/features/tasks/components/TaskKanbanBoard.tsx

- **CREATE**: 看板主组件
- **PATTERN**: 组合KanbanColumn组件
- **IMPLEMENTATION**:
  ```typescript
  'use client';
  
  import { useTaskKanban } from '../hooks/useTaskKanban';
  import { KanbanColumn } from './KanbanColumn';
  import { QueueStatus } from '@/lib/types';
  
  interface TaskKanbanBoardProps {
    projectId?: string;
  }
  
  export function TaskKanbanBoard({ projectId }: TaskKanbanBoardProps) {
    const { kanban, isLoading, updateTaskStatus } = useTaskKanban(projectId);
    
    if (isLoading) return <div>Loading...</div>;
    if (!kanban) return <div>No data</div>;
    
    const handleDrop = (taskId: string, newStatus: QueueStatus) => {
      updateTaskStatus({ taskId, status: newStatus });
    };
    
    return (
      <div className="flex gap-4 overflow-x-auto p-4">
        <KanbanColumn
          title="Scheduled"
          status="scheduled"
          tasks={kanban.scheduled}
          count={kanban.scheduled.length}
          onDrop={handleDrop}
        />
        <KanbanColumn
          title="Queue"
          status="queued"
          tasks={kanban.queued}
          count={kanban.queued.length}
          onDrop={handleDrop}
        />
        <KanbanColumn
          title="In Progress"
          status="in_progress"
          tasks={kanban.in_progress}
          count={kanban.in_progress.length}
          onDrop={handleDrop}
        />
        <KanbanColumn
          title="Done"
          status="done"
          tasks={kanban.done}
          count={kanban.done.length}
          onDrop={handleDrop}
        />
      </div>
    );
  }
  ```
- **VALIDATE**: `cd frontend && npm run build`


### Task 4.8: CREATE frontend/src/app/tasks/kanban/page.tsx

- **CREATE**: 看板页面
- **PATTERN**: 复用现有page.tsx结构
- **IMPLEMENTATION**:
  ```typescript
  import { TaskKanbanBoard } from '@/features/tasks/components/TaskKanbanBoard';
  import { Container } from '@/components/layout/Container';
  import { Header } from '@/components/layout/Header';
  
  export default function KanbanPage() {
    return (
      <>
        <Header />
        <Container>
          <div className="py-8">
            <h1 className="text-3xl font-bold mb-6">Task Queue</h1>
            <TaskKanbanBoard />
          </div>
        </Container>
      </>
    );
  }
  ```
- **VALIDATE**: `cd frontend && npm run build`

### Phase 5: Testing & Integration

### Task 5.1: CREATE backend/tests/test_task_scheduler.py

- **CREATE**: Scheduler单元测试
- **PATTERN**: 复用现有测试模式 (test_api_tasks.py)
- **IMPLEMENTATION**:
  ```python
  import pytest
  from datetime import datetime, timedelta, UTC
  from app.models.task import Task, QueueStatus
  from app.services.task_scheduler import TaskScheduler
  
  @pytest.mark.asyncio
  async def test_scheduler_moves_due_tasks(db_session):
      """Test scheduler moves scheduled tasks to queue when due."""
      past_time = datetime.now(UTC) - timedelta(minutes=5)
      task = Task(
          conversation_id=uuid.uuid4(),
          project_id=uuid.uuid4(),
          goal="test task",
          queue_status=QueueStatus.SCHEDULED,
          scheduled_at=past_time.replace(tzinfo=None)
      )
      db_session.add(task)
      await db_session.commit()
      
      scheduler = TaskScheduler()
      await scheduler._process_scheduled_tasks()
      
      await db_session.refresh(task)
      assert task.queue_status == QueueStatus.QUEUED
  
  @pytest.mark.asyncio
  async def test_scheduler_ignores_future_tasks(db_session):
      """Test scheduler does not move future scheduled tasks."""
      future_time = datetime.now(UTC) + timedelta(hours=1)
      task = Task(
          conversation_id=uuid.uuid4(),
          project_id=uuid.uuid4(),
          goal="future task",
          queue_status=QueueStatus.SCHEDULED,
          scheduled_at=future_time.replace(tzinfo=None)
      )
      db_session.add(task)
      await db_session.commit()
      
      scheduler = TaskScheduler()
      await scheduler._process_scheduled_tasks()
      
      await db_session.refresh(task)
      assert task.queue_status == QueueStatus.SCHEDULED
  ```
- **VALIDATE**: `cd backend && uv run pytest tests/test_task_scheduler.py -v`

### Task 5.2: UPDATE backend/tests/test_api_tasks.py - Add queue status tests

- **ADD**: 测试新的queue status端点
- **IMPLEMENTATION**:
  ```python
  @pytest.mark.asyncio
  async def test_update_task_queue_status(client, db_session):
      """Test updating task queue status."""
      task = Task(
          conversation_id=uuid.uuid4(),
          project_id=uuid.uuid4(),
          goal="test",
          queue_status=QueueStatus.SCHEDULED
      )
      db_session.add(task)
      await db_session.commit()
      
      response = await client.patch(
          f"/api/tasks/{task.id}/queue-status?queue_status=queued"
      )
      assert response.status_code == 200
      data = response.json()
      assert data["queue_status"] == "queued"
  
  @pytest.mark.asyncio
  async def test_get_kanban_board(client, db_session):
      """Test fetching kanban board data."""
      project_id = uuid.uuid4()
      for status in [QueueStatus.SCHEDULED, QueueStatus.QUEUED, QueueStatus.DONE]:
          task = Task(
              conversation_id=uuid.uuid4(),
              project_id=project_id,
              goal=f"task {status.value}",
              queue_status=status
          )
          db_session.add(task)
      await db_session.commit()
      
      response = await client.get(f"/api/tasks/kanban?project_id={project_id}")
      assert response.status_code == 200
      data = response.json()
      assert len(data["scheduled"]) == 1
      assert len(data["queued"]) == 1
      assert len(data["done"]) == 1
  ```
- **VALIDATE**: `cd backend && uv run pytest tests/test_api_tasks.py -v`


---

## TESTING STRATEGY

### Unit Tests

**Backend**:
- TaskScheduler逻辑测试（移动到期任务）
- Queue status转换API测试
- Kanban board数据聚合测试

**Frontend**:
- TaskCard组件渲染测试
- KanbanColumn组件测试
- useTaskKanban Hook测试

### Integration Tests

**End-to-End Flow**:
1. 创建scheduled任务
2. 等待scheduler处理
3. 验证任务移到queued
4. Worker执行任务
5. 验证任务移到done

### Edge Cases

- Scheduler处理大量到期任务（性能测试）
- 并发更新queue_status（竞态条件）
- scheduled_at为null的任务（不应被处理）
- 拖拽到相同列（无操作）
- 网络错误时的UI状态

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Backend linting
cd backend && uv run ruff check app/

# Frontend linting
cd frontend && npm run lint

# Type checking
cd frontend && npm run type-check
```

### Level 2: Unit Tests

```bash
# Backend unit tests
cd backend && uv run pytest tests/test_task_scheduler.py -v
cd backend && uv run pytest tests/test_api_tasks.py -v

# Frontend component tests
cd frontend && npm run test
```

### Level 3: Integration Tests

```bash
# Database migration
cd backend && uv run alembic upgrade head

# Full backend test suite
cd backend && uv run pytest tests/ -v

# Frontend build
cd frontend && npm run build
```

### Level 4: Manual Validation

```bash
# 1. Start all services
docker compose up -d

# 2. Create a scheduled task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "UUID",
    "project_id": "UUID",
    "goal": "Test scheduled task",
    "scheduled_at": "2026-03-17T18:00:00",
    "priority": 5,
    "assigned_agent": "Gumbo"
  }'

# 3. Get kanban board
curl http://localhost:8000/api/tasks/kanban

# 4. Update queue status
curl -X PATCH http://localhost:8000/api/tasks/{task_id}/queue-status?queue_status=queued

# 5. Open frontend kanban
# Navigate to http://localhost:3000/tasks/kanban
# Verify 4 columns are displayed
# Verify tasks can be dragged between columns
```


---

## ACCEPTANCE CRITERIA

- [ ] Task模型包含queue_status, scheduled_at, priority, assigned_agent字段
- [ ] 数据库迁移成功执行，索引创建正确
- [ ] TaskScheduler每30秒自动处理到期任务
- [ ] API支持按queue_status过滤任务
- [ ] API支持更新任务队列状态
- [ ] API返回按状态分组的kanban数据
- [ ] Frontend显示4列看板（Scheduled/Queue/In Progress/Done）
- [ ] 任务卡片显示agent、时间、优先级信息
- [ ] 看板每5秒自动刷新
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 手动测试验证完整流程
- [ ] 无性能回归（查询时间<100ms）

---

## COMPLETION CHECKLIST

- [ ] 所有Phase 1-5任务按顺序完成
- [ ] 每个任务的验证命令执行成功
- [ ] 数据库迁移脚本测试通过
- [ ] Backend所有测试通过（pytest）
- [ ] Frontend构建成功（npm run build）
- [ ] Scheduler服务正常启动和关闭
- [ ] Kanban UI正确显示和更新
- [ ] 手动端到端测试成功
- [ ] 代码遵循项目规范
- [ ] 无linting错误

---

## NOTES

### Design Decisions

**为什么添加queue_status而不是复用TaskRun.status？**
- Task和TaskRun是不同层次的概念
- Task代表"要做什么"，TaskRun代表"某次执行"
- queue_status管理Task在队列中的位置
- 一个Task可以有多个TaskRun（重试）

**为什么使用APScheduler而不是Celery Beat？**
- APScheduler更轻量，适合简单的定时任务
- 不需要额外的broker配置
- 与FastAPI的async模式集成更好
- 可以后续升级到Celery Beat

**为什么每30秒检查一次而不是实时？**
- 平衡实时性和数据库负载
- 30秒延迟对任务调度场景可接受
- 可以通过配置调整间隔

**拖拽功能的简化实现**
- 当前版本：点击更新状态（不使用React DnD）
- 原因：React DnD增加复杂度，MVP阶段可以简化
- 后续可以升级为真正的拖拽

### Performance Considerations

**数据库索引**:
- queue_status: 频繁过滤查询
- scheduled_at: 排序和范围查询
- priority: 排序查询

**查询优化**:
- Kanban board查询一次获取所有状态
- 使用内存分组而不是多次查询

**Frontend优化**:
- 5秒轮询间隔（可配置）
- 考虑后续升级为WebSocket实时推送

### Migration Strategy

**向后兼容**:
- 新字段有默认值（queue_status=SCHEDULED, priority=0）
- 现有Task自动获得默认值
- 现有API继续工作

**渐进式采用**:
- 用户可以继续使用旧的Task创建方式
- 新的Kanban UI是可选功能
- Scheduler不影响现有工作流

