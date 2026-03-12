# Feature: Run API and Event Streaming

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement Run-specific API endpoints and WebSocket event streaming to enable real-time monitoring of task execution. This feature adds direct access to individual task runs and the ability to cancel running tasks, plus a WebSocket connection for streaming execution events to clients.

## User Story

As a user
I want to monitor task execution in real-time and cancel running tasks
So that I can observe progress, debug issues, and stop tasks that are taking too long or going in the wrong direction

## Problem Statement

Currently, the system has task and task run models, but lacks:
1. Direct access to individual runs by ID (must go through /tasks/{id}/runs)
2. Ability to cancel running tasks
3. Real-time event streaming for task progress updates
4. Observable execution transparency for users

## Solution Statement

Add two new REST endpoints for run management and implement WebSocket-based event streaming:
- GET /api/runs/{run_id} - Retrieve a specific run
- POST /api/runs/{run_id}/cancel - Cancel a running task
- WebSocket /api/runs/{run_id}/stream - Stream real-time events

Use FastAPI's native WebSocket support with an in-memory event broadcaster for MVP simplicity.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: backend/app/routers, backend/app/services
**Dependencies**: FastAPI WebSockets (already included)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/app/routers/tasks.py` (lines 1-77) - Why: Existing task router pattern to follow
- `backend/app/models/task.py` (lines 1-50) - Why: TaskRun model and TaskStatus enum
- `backend/app/schemas/task.py` (lines 33-44) - Why: TaskRunResponse schema
- `backend/app/main.py` (lines 1-24) - Why: Router registration pattern
- `backend/app/database.py` - Why: Database session dependency pattern

### New Files to Create

- `backend/app/routers/runs.py` - Run-specific API endpoints
- `backend/app/services/event_broadcaster.py` - WebSocket event broadcasting
- `backend/tests/test_api_runs.py` - Unit tests for run endpoints

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
  - Specific section: WebSocket endpoint definition and connection handling
  - Why: Required for implementing real-time event streaming
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
  - Specific section: Dependency injection in path operations
  - Why: Database session and service injection patterns
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - Specific section: Async session usage
  - Why: Proper async database operations

### Patterns to Follow

**Router Pattern:**
```python
# From tasks.py:10-20
router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
```

**Status Enum:**
```python
# From task.py:10-15
class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

**Error Handling:**
```python
# From tasks.py:34-36
if not task:
    raise HTTPException(status_code=404, detail="Task not found")
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create the runs router and event broadcaster service.

**Tasks:**
- Create runs.py router with basic structure
- Create event_broadcaster.py service for WebSocket management
- Set up in-memory connection manager

### Phase 2: Core Implementation

Implement REST endpoints and WebSocket streaming.

**Tasks:**
- Implement GET /api/runs/{run_id}
- Implement POST /api/runs/{run_id}/cancel
- Implement WebSocket /api/runs/{run_id}/stream
- Add event broadcasting logic

### Phase 3: Integration

Register router and connect to main application.

**Tasks:**
- Register runs router in main.py
- Add CORS configuration for WebSocket
- Ensure database session handling

### Phase 4: Testing & Validation

Create comprehensive tests.

**Tasks:**
- Unit tests for GET /runs/{id}
- Unit tests for POST /runs/{id}/cancel
- WebSocket connection tests
- Integration tests for event flow

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: CREATE backend/app/services/event_broadcaster.py

- **IMPLEMENT**: WebSocket connection manager for broadcasting events
- **PATTERN**: Singleton pattern for managing active connections
- **IMPORTS**: fastapi.WebSocket, asyncio, typing
- **CODE**:
```python
"""Event broadcasting service for WebSocket connections."""
from typing import Dict, Set
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class EventBroadcaster:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.connections:
            self.connections[run_id] = set()
        self.connections[run_id].add(websocket)
        logger.info("websocket_connected", run_id=run_id)

    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.connections:
            self.connections[run_id].discard(websocket)
            if not self.connections[run_id]:
                del self.connections[run_id]
        logger.info("websocket_disconnected", run_id=run_id)

    async def broadcast(self, run_id: str, event: dict):
        if run_id not in self.connections:
            return
        disconnected = set()
        for websocket in self.connections[run_id]:
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.error("websocket_send_failed", error=str(e))
                disconnected.add(websocket)
        for websocket in disconnected:
            self.disconnect(run_id, websocket)


broadcaster = EventBroadcaster()
```
- **VALIDATE**: `cd backend && python -c "from app.services.event_broadcaster import broadcaster; print('OK')"`

### Task 2: CREATE backend/app/routers/runs.py

- **IMPLEMENT**: Run-specific API endpoints
- **PATTERN**: Mirror tasks.py router structure
- **IMPORTS**: FastAPI, SQLAlchemy, WebSocket, uuid, datetime
- **CODE**:
```python
"""Run API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime
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
    run.completed_at = datetime.utcnow()
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
```
- **VALIDATE**: `cd backend && python -c "from app.routers.runs import router; print('OK')"`

### Task 3: UPDATE backend/app/main.py

- **IMPLEMENT**: Register runs router
- **PATTERN**: Follow existing router registration (lines 16-19)
- **IMPORTS**: Add runs to imports
- **CHANGE**:
```python
# Line 4: Update import
from app.routers import projects, conversations, tasks, rag, runs

# After line 19: Add router registration
app.include_router(runs.router)
```
- **VALIDATE**: `cd backend && python -c "from app.main import app; print('OK')"`

### Task 4: CREATE backend/app/services/__init__.py

- **IMPLEMENT**: Make services a proper package
- **CODE**:
```python
"""Services package."""
```
- **VALIDATE**: `cd backend && python -c "from app.services import event_broadcaster; print('OK')"`

### Task 5: CREATE backend/tests/test_api_runs.py

- **IMPLEMENT**: Unit tests for run endpoints
- **PATTERN**: Mirror test_api_tasks.py structure
- **IMPORTS**: pytest, httpx, AsyncClient, uuid
- **CODE**:
```python
"""Tests for Run API endpoints."""
import pytest
from httpx import AsyncClient
from app.main import app
from app.models.task import TaskStatus


@pytest.mark.asyncio
async def test_get_run(client: AsyncClient, test_task_run):
    """Test GET /api/runs/{run_id}."""
    response = await client.get(f"/api/runs/{test_task_run.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_task_run.id)
    assert data["status"] == test_task_run.status.value


@pytest.mark.asyncio
async def test_get_nonexistent_run(client: AsyncClient):
    """Test GET /api/runs/{run_id} with invalid ID."""
    import uuid
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/runs/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_run(client: AsyncClient, test_task_run):
    """Test POST /api/runs/{run_id}/cancel."""
    # Update run to RUNNING status
    test_task_run.status = TaskStatus.RUNNING

    response = await client.post(f"/api/runs/{test_task_run.id}/cancel")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_cancel_completed_run(client: AsyncClient, test_task_run):
    """Test canceling already completed run."""
    test_task_run.status = TaskStatus.COMPLETED

    response = await client.post(f"/api/runs/{test_task_run.id}/cancel")
    assert response.status_code == 400
```
- **VALIDATE**: `cd backend && uv run pytest tests/test_api_runs.py -v`

---

## TESTING STRATEGY

### Unit Tests

**Framework**: pytest with pytest-asyncio
**Location**: backend/tests/test_api_runs.py
**Coverage Target**: 100% of runs.py endpoints

**Test Cases**:
1. GET /api/runs/{run_id} - success
2. GET /api/runs/{run_id} - not found (404)
3. POST /api/runs/{run_id}/cancel - success
4. POST /api/runs/{run_id}/cancel - already completed (400)
5. POST /api/runs/{run_id}/cancel - not found (404)

**Fixtures Needed**:
- test_task_run: Create a TaskRun instance for testing

### Integration Tests

**WebSocket Testing**:
- Connection establishment
- Event broadcasting
- Disconnection handling
- Multiple clients per run

### Edge Cases

- Canceling PENDING run (should succeed)
- Canceling RUNNING run (should succeed)
- Canceling COMPLETED run (should fail)
- Canceling FAILED run (should fail)
- Canceling CANCELLED run (should fail)
- WebSocket connection to non-existent run
- Multiple WebSocket connections to same run
- WebSocket disconnection cleanup

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd backend && python -c "from app.routers.runs import router; from app.services.event_broadcaster import broadcaster; print('Import check: OK')"
```

**Expected**: "Import check: OK"

### Level 2: Unit Tests

```bash
cd backend && uv run pytest tests/test_api_runs.py -v
```

**Expected**: All tests pass

### Level 3: Full Test Suite

```bash
cd backend && uv run pytest tests/ -v
```

**Expected**: All tests pass (existing + new)

### Level 4: Manual Validation

Start the backend server:
```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

Test GET endpoint:
```bash
curl http://localhost:8000/api/runs/{run_id}
```

Test cancel endpoint:
```bash
curl -X POST http://localhost:8000/api/runs/{run_id}/cancel
```

Test WebSocket (using wscat or browser):
```bash
wscat -c ws://localhost:8000/api/runs/{run_id}/stream
```

---

## ACCEPTANCE CRITERIA

- [ ] GET /api/runs/{run_id} returns run details
- [ ] GET /api/runs/{run_id} returns 404 for non-existent runs
- [ ] POST /api/runs/{run_id}/cancel cancels PENDING/RUNNING runs
- [ ] POST /api/runs/{run_id}/cancel returns 400 for completed runs
- [ ] POST /api/runs/{run_id}/cancel broadcasts cancellation event
- [ ] WebSocket /api/runs/{run_id}/stream accepts connections
- [ ] WebSocket broadcasts events to all connected clients
- [ ] WebSocket handles disconnections gracefully
- [ ] All unit tests pass (4+ tests)
- [ ] No regressions in existing tests
- [ ] Code follows FastAPI patterns
- [ ] Proper error handling with HTTPException
- [ ] Structured logging for WebSocket events

---

## COMPLETION CHECKLIST

- [ ] Task 1: EventBroadcaster service created
- [ ] Task 2: Runs router created with 3 endpoints
- [ ] Task 3: Router registered in main.py
- [ ] Task 4: Services package initialized
- [ ] Task 5: Unit tests created
- [ ] All validation commands pass
- [ ] Full test suite passes
- [ ] Manual WebSocket testing successful
- [ ] Code reviewed for quality

---

## NOTES

### Design Decisions

1. **In-Memory Event Broadcaster**
   - Rationale: Simple MVP implementation, no external dependencies
   - Trade-off: Events lost on server restart, no horizontal scaling
   - Future: Replace with Redis pub/sub for production

2. **WebSocket Keep-Alive**
   - Implementation: Client sends periodic messages to keep connection alive
   - Server listens but doesn't process messages (ping/pong pattern)

3. **Run Cancellation**
   - Only PENDING/RUNNING runs can be cancelled
   - Sets status to CANCELLED and completed_at timestamp
   - Broadcasts event to connected clients
   - Note: Actual task execution cancellation requires worker integration (future)

4. **Event Format**
   - Simple JSON: `{"type": "status_change", "status": "cancelled"}`
   - Extensible for future event types (tool_call, log_entry, etc.)

### Future Enhancements

- Add Redis pub/sub for distributed event broadcasting
- Implement event persistence (store events in database)
- Add authentication/authorization for WebSocket connections
- Support multiple event types (progress, logs, tool calls)
- Add reconnection logic with event replay
- Implement backpressure handling for slow clients
- Add metrics for WebSocket connections

### Security Considerations

- WebSocket connections are unauthenticated in MVP
- No rate limiting on connections
- No validation of run ownership
- Production: Add JWT authentication, rate limiting, ownership checks
