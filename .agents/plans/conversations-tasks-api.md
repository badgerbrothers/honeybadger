# Feature: FastAPI Conversations & Tasks API

## Feature Description

Implement two independent API resources - Conversations and Tasks - with clear architectural boundaries. Conversations manage chat interfaces within projects, while Tasks represent goal-oriented work units. The key design principle is separation: Conversations do NOT directly create Tasks; instead, Tasks are created independently with references to both conversation_id and project_id.

This establishes the foundation for the task execution workflow: users initiate conversations, send messages, and explicitly create tasks that reference those conversations.

## User Story

As a frontend developer
I want to manage conversations and tasks through separate REST APIs
So that I can build a UI where users chat in conversations and explicitly delegate work to tasks, maintaining clear separation between chat interface and task execution

## Problem Statement

The backend currently only has Projects API. To enable the core Badgers workflow, we need:
- Conversation management (create, list, update conversations within projects)
- Message management (add messages to conversations)
- Task management (create tasks linked to conversations and projects)
- TaskRun management (trigger task executions)
- Clear API boundaries preventing tight coupling between resources

## Solution Statement

Implement two independent APIRouter modules:
1. **Conversations API** (`/api/conversations`) - CRUD for conversations plus nested messages endpoint
2. **Tasks API** (`/api/tasks`) - CRUD for tasks plus nested runs endpoint

Key architectural decision: Tasks are created via `POST /api/tasks` with `conversation_id` in the request body, NOT via `POST /api/conversations/{id}/tasks`. This maintains loose coupling and follows RESTful best practices.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: Backend API Layer
**Dependencies**: FastAPI, SQLAlchemy, existing models and schemas

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**IMPORTANT: READ THESE BEFORE IMPLEMENTING!**

- `backend/app/routers/projects.py` - Existing router pattern to mirror (CRUD structure, error handling, async patterns)
- `backend/app/models/conversation.py` - Conversation and Message models with relationships
- `backend/app/models/task.py` - Task and TaskRun models with TaskStatus enum
- `backend/app/schemas/conversation.py` - ConversationCreate, ConversationUpdate, ConversationResponse, MessageCreate, MessageResponse
- `backend/app/schemas/task.py` - TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse
- `backend/app/main.py` - Where routers are registered
- `backend/tests/test_api_projects.py` - Test pattern to follow
- `backend/tests/conftest.py` - Test fixtures (event_loop, reset_db)

### New Files to Create

- `backend/app/routers/conversations.py` - Conversations API endpoints
- `backend/app/routers/tasks.py` - Tasks API endpoints
- `backend/tests/test_api_conversations.py` - Conversations API integration tests
- `backend/tests/test_api_tasks.py` - Tasks API integration tests

### Relevant Documentation

**YOU SHOULD READ THESE BEFORE IMPLEMENTING!**

- [FastAPI Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/)
  - UUID path parameters
  - Why: All resources use UUID primary keys
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/)
  - Optional filtering parameters
  - Why: Need to filter conversations by project_id, tasks by conversation_id
- [FastAPI Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)
  - response_model with lists
  - Why: List endpoints return list[ResponseSchema]
- [SQLAlchemy Async Queries](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - select() with where() clauses
  - Why: Filtering queries need where conditions

### Patterns to Follow

**Router Pattern** (from projects.py):
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.database import get_db

router = APIRouter(prefix="/api/resource", tags=["resource"])

@router.get("/", response_model=list[ResourceResponse])
async def list_resources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Resource))
    return result.scalars().all()

@router.post("/", response_model=ResourceResponse, status_code=201)
async def create_resource(data: ResourceCreate, db: AsyncSession = Depends(get_db)):
    db_obj = Resource(**data.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
```

**Error Handling Pattern**:
```python
if not obj:
    raise HTTPException(status_code=404, detail="Resource not found")
```

**Query Filtering Pattern**:
```python
# Filter by foreign key
query = select(Resource).where(Resource.parent_id == parent_id)
result = await db.execute(query)
```

**Nested Resource Pattern**:
```python
# GET /parent/{parent_id}/children
@router.get("/{parent_id}/children", response_model=list[ChildResponse])
async def list_children(parent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Verify parent exists
    parent = await db.execute(select(Parent).where(Parent.id == parent_id))
    if not parent.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Parent not found")
    # Get children
    result = await db.execute(select(Child).where(Child.parent_id == parent_id))
    return result.scalars().all()
```

---

## IMPLEMENTATION PLAN

### Phase 1: Conversations Router

Implement Conversations CRUD and nested Messages endpoint.

**Tasks:**
- Create conversations.py router with CRUD endpoints
- Add nested messages endpoint (GET and POST)
- Implement query filtering by project_id
- Register router in main.py

### Phase 2: Tasks Router

Implement Tasks CRUD and nested TaskRuns endpoint.

**Tasks:**
- Create tasks.py router with CRUD endpoints
- Add nested runs endpoint (GET and POST)
- Implement query filtering by conversation_id and project_id
- Register router in main.py

### Phase 3: Integration Tests

Create comprehensive test coverage for both APIs.

**Tasks:**
- Test Conversations CRUD operations
- Test Messages nested resource
- Test Tasks CRUD operations
- Test TaskRuns nested resource
- Test filtering and error cases

### Phase 4: Validation

Run all validation commands to ensure quality.

**Tasks:**
- Linting checks
- Full test suite
- Coverage verification

---

## STEP-BY-STEP TASKS

### CREATE backend/app/routers/conversations.py

- **IMPLEMENT**: APIRouter with prefix="/api/conversations", tags=["conversations"]
- **IMPLEMENT**: 5 CRUD endpoints (list, create, get, update, delete)
- **IMPLEMENT**: 2 nested message endpoints (list messages, create message)
- **IMPORTS**: `from fastapi import APIRouter, Depends, HTTPException, Query`
- **IMPORTS**: `from sqlalchemy.ext.asyncio import AsyncSession`
- **IMPORTS**: `from sqlalchemy import select`
- **IMPORTS**: `import uuid`
- **IMPORTS**: `from app.database import get_db`
- **IMPORTS**: `from app.models.conversation import Conversation, Message`
- **IMPORTS**: `from app.models.project import Project`
- **IMPORTS**: `from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse, MessageCreate, MessageResponse`
- **PATTERN**: Mirror projects.py router structure
- **ENDPOINTS**:
  - `GET /` - List conversations (optional project_id query param)
  - `POST /` - Create conversation (requires project_id in body)
  - `GET /{conversation_id}` - Get conversation
  - `PATCH /{conversation_id}` - Update conversation
  - `DELETE /{conversation_id}` - Delete conversation
  - `GET /{conversation_id}/messages` - List messages in conversation
  - `POST /{conversation_id}/messages` - Add message to conversation
- **VALIDATE**: `cd backend && uv run python -c "from app.routers.conversations import router; print('OK')"`

### CREATE backend/app/routers/tasks.py

- **IMPLEMENT**: APIRouter with prefix="/api/tasks", tags=["tasks"]
- **IMPLEMENT**: 5 CRUD endpoints (list, create, get, update, delete)
- **IMPLEMENT**: 2 nested run endpoints (list runs, create run)
- **IMPORTS**: `from fastapi import APIRouter, Depends, HTTPException, Query`
- **IMPORTS**: `from sqlalchemy.ext.asyncio import AsyncSession`
- **IMPORTS**: `from sqlalchemy import select`
- **IMPORTS**: `import uuid`
- **IMPORTS**: `from datetime import datetime`
- **IMPORTS**: `from app.database import get_db`
- **IMPORTS**: `from app.models.task import Task, TaskRun, TaskStatus`
- **IMPORTS**: `from app.models.conversation import Conversation`
- **IMPORTS**: `from app.models.project import Project`
- **IMPORTS**: `from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse`
- **PATTERN**: Mirror projects.py router structure
- **ENDPOINTS**:
  - `GET /` - List tasks (optional conversation_id and project_id query params)
  - `POST /` - Create task (requires conversation_id and project_id in body)
  - `GET /{task_id}` - Get task
  - `PATCH /{task_id}` - Update task
  - `DELETE /{task_id}` - Delete task
  - `GET /{task_id}/runs` - List task runs
  - `POST /{task_id}/runs` - Create new task run (status=PENDING)
- **VALIDATE**: `cd backend && uv run python -c "from app.routers.tasks import router; print('OK')"`

### UPDATE backend/app/main.py

- **IMPLEMENT**: Register conversations router
- **IMPLEMENT**: Register tasks router
- **IMPORTS**: `from app.routers import projects, conversations, tasks`
- **PATTERN**:
```python
app.include_router(projects.router)
app.include_router(conversations.router)
app.include_router(tasks.router)
```
- **VALIDATE**: `cd backend && uv run python -c "from app.main import app; print('OK')"`


### CREATE backend/tests/test_api_conversations.py

- **IMPLEMENT**: Integration tests for Conversations API
- **IMPORTS**: `import pytest`
- **IMPORTS**: `from httpx import AsyncClient, ASGITransport`
- **IMPORTS**: `from app.main import app`
- **PATTERN**: Mirror test_api_projects.py structure
- **TEST CASES**:
  - `test_create_conversation` - Create conversation with project_id
  - `test_list_conversations` - List all conversations
  - `test_list_conversations_filtered` - Filter by project_id query param
  - `test_get_conversation` - Get single conversation
  - `test_update_conversation` - Update conversation title
  - `test_delete_conversation` - Delete conversation
  - `test_get_nonexistent_conversation` - 404 error
  - `test_add_message_to_conversation` - POST message to conversation
  - `test_list_messages` - GET messages from conversation
- **VALIDATE**: `cd backend && uv run pytest tests/test_api_conversations.py -v`

### CREATE backend/tests/test_api_tasks.py

- **IMPLEMENT**: Integration tests for Tasks API
- **IMPORTS**: `import pytest`
- **IMPORTS**: `from httpx import AsyncClient, ASGITransport`
- **IMPORTS**: `from app.main import app`
- **PATTERN**: Mirror test_api_projects.py structure
- **TEST CASES**:
  - `test_create_task` - Create task with conversation_id and project_id
  - `test_list_tasks` - List all tasks
  - `test_list_tasks_filtered` - Filter by conversation_id or project_id
  - `test_get_task` - Get single task
  - `test_update_task` - Update task goal
  - `test_delete_task` - Delete task
  - `test_get_nonexistent_task` - 404 error
  - `test_create_task_run` - POST new run for task
  - `test_list_task_runs` - GET runs from task
- **VALIDATE**: `cd backend && uv run pytest tests/test_api_tasks.py -v`

---

## TESTING STRATEGY

### Integration Tests

Use httpx AsyncClient with ASGITransport to test API endpoints end-to-end.

**Conversations API Tests:**
- CRUD operations for conversations
- Nested messages resource (GET and POST)
- Query filtering by project_id
- 404 errors for nonexistent resources
- Foreign key validation (project_id must exist)

**Tasks API Tests:**
- CRUD operations for tasks
- Nested runs resource (GET and POST)
- Query filtering by conversation_id and project_id
- 404 errors for nonexistent resources
- Foreign key validation (conversation_id and project_id must exist)

### Edge Cases

- Create conversation with nonexistent project_id (should fail)
- Create task with nonexistent conversation_id or project_id (should fail)
- Add message to nonexistent conversation (404)
- Create run for nonexistent task (404)
- Filter with invalid UUID format
- Empty title/goal validation

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd backend && uv run ruff check app/routers/
```

**Expected**: All checks passed

### Level 2: Import Validation

```bash
cd backend && uv run python -c "from app.main import app; from app.routers.conversations import router; from app.routers.tasks import router as tasks_router; print('Imports OK')"
```

**Expected**: Imports OK

### Level 3: Unit Tests

```bash
cd backend && uv run pytest tests/test_api_conversations.py tests/test_api_tasks.py -v
```

**Expected**: All tests pass

### Level 4: Full Test Suite

```bash
cd backend && uv run pytest -v
```

**Expected**: All tests pass (including existing projects tests)

### Level 5: Coverage Check

```bash
cd backend && uv run pytest --cov=app --cov-report=term-missing
```

**Expected**: Coverage >= 80%

---

## ACCEPTANCE CRITERIA

- [ ] Conversations router created with 5 CRUD endpoints
- [ ] Conversations router has nested messages endpoints (GET and POST)
- [ ] Conversations list endpoint supports project_id query filtering
- [ ] Tasks router created with 5 CRUD endpoints
- [ ] Tasks router has nested runs endpoints (GET and POST)
- [ ] Tasks list endpoint supports conversation_id and project_id query filtering
- [ ] Both routers registered in main.py
- [ ] Tasks are created independently via POST /api/tasks (NOT nested under conversations)
- [ ] All endpoints use correct schemas (Create, Update, Response)
- [ ] All endpoints use AsyncSession dependency injection
- [ ] 404 errors handled correctly for nonexistent resources
- [ ] Foreign key constraints validated (project_id, conversation_id exist)
- [ ] Integration tests cover all CRUD operations
- [ ] Integration tests cover nested resources (messages, runs)
- [ ] Integration tests cover query filtering
- [ ] Integration tests cover error cases
- [ ] All linting checks pass
- [ ] All tests pass with >= 80% coverage

---

## COMPLETION CHECKLIST

- [ ] conversations.py router created
- [ ] tasks.py router created
- [ ] Both routers registered in main.py
- [ ] test_api_conversations.py created
- [ ] test_api_tasks.py created
- [ ] All validation commands pass
- [ ] Linting clean
- [ ] Full test suite passes
- [ ] Coverage >= 80%

---

## NOTES

**Design Decisions:**

1. **Independent Task Creation**: Tasks are created via `POST /api/tasks` with `conversation_id` in body, NOT via nested endpoint under conversations. This maintains clear boundaries and follows RESTful principles.

2. **Query Filtering**: List endpoints use optional query parameters for filtering rather than requiring nested routes. This provides flexibility for frontend to query across multiple parents.

3. **Nested Resources**: Messages and TaskRuns use nested endpoints because they're tightly coupled to their parents and rarely accessed independently.

4. **Foreign Key Validation**: When creating resources with foreign keys, verify parent exists and return 404 if not found.

5. **TaskRun Creation**: POST /api/tasks/{task_id}/runs creates a new run with status=PENDING. The actual execution logic (worker orchestration) is out of scope for this plan.

**Implementation Order Rationale:**

- Conversations first (simpler, no status enum complexity)
- Tasks second (builds on conversation patterns)
- Tests after implementation (verify functionality)
- Validation last (ensure quality)

**Future Considerations:**

- Pagination for list endpoints (limit/offset query params)
- Sorting options (order_by query param)
- TaskRun status transitions and validation
- WebSocket support for real-time task updates
- Authentication and authorization middleware
