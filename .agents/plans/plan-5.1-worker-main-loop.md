# Feature: Worker Main Loop Implementation

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement the Worker main loop (`worker/main.py`) that serves as the execution engine for the Badgers MVP platform. This component bridges the Backend API and the Agent orchestration system by continuously polling for pending tasks, managing their lifecycle through isolated Docker sandboxes, coordinating Agent execution, and broadcasting real-time progress events to connected clients.

The Worker is a standalone Python process that operates independently from the FastAPI backend, communicating through a shared PostgreSQL database and Redis queue. It transforms task definitions into executable workflows by:
1. Retrieving pending TaskRuns from the database or Redis queue
2. Creating isolated Docker sandboxes for safe execution
3. Loading appropriate AI models and skill templates
4. Initializing the Agent with configured tools
5. Executing the reasoning-action-observation loop
6. Persisting results and artifacts
7. Broadcasting status updates via WebSocket
8. Cleaning up resources

## User Story

As a **system operator**
I want **a reliable worker process that autonomously executes queued tasks**
So that **users can delegate complex workflows to AI agents without blocking the API or risking system stability**

## Problem Statement

Currently, the Badgers MVP has all the necessary components for task execution (Agent orchestrator, sandbox manager, tool system, model abstraction) but lacks the critical integration layer that ties them together. Without `worker/main.py`:

- TaskRuns remain in PENDING status indefinitely
- No process monitors the queue for new work
- Sandboxes are never created or managed
- Agent execution never triggers
- Users see no progress updates
- The system cannot fulfill its core promise of autonomous task execution

The missing Worker main loop prevents the entire platform from functioning end-to-end.

## Solution Statement

Create `worker/main.py` as the central orchestration point that:

1. **Polling Loop**: Continuously checks for PENDING TaskRuns (via database polling or Redis queue consumption)
2. **Task Lifecycle Management**: Updates TaskRun status through PENDING → RUNNING → COMPLETED/FAILED transitions
3. **Sandbox Orchestration**: Creates, manages, and destroys Docker containers per TaskRun
4. **Database Integration**: Persists SandboxSession records and updates TaskRun metadata
5. **Agent Coordination**: Initializes Agent with appropriate model, tools, and skill configuration
6. **Event Broadcasting**: Emits real-time progress events to WebSocket clients
7. **Error Handling**: Gracefully handles failures, logs comprehensively, and ensures cleanup
8. **Graceful Shutdown**: Responds to signals (SIGTERM/SIGINT) and completes in-flight tasks

The implementation follows async/await patterns throughout, uses structlog for observability, and mirrors existing patterns from the Agent and sandbox components.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**:
- Worker process (new entry point)
- Backend database (TaskRun, SandboxSession models)
- Event broadcasting (WebSocket integration)
- Redis queue (task distribution)

**Dependencies**:
- asyncio (async event loop)
- sqlalchemy (async database operations)
- redis (task queue - optional, can use DB polling initially)
- structlog (structured logging)
- signal (graceful shutdown)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Core Components:**
- `worker/orchestrator/agent.py` (lines 15-119) - Agent class with run() method, tool execution pattern
- `worker/sandbox/manager.py` (lines 7-56) - SandboxManager lifecycle, async context manager pattern
- `worker/models/factory.py` - Model provider factory for creating LLM instances
- `worker/tools/__init__.py` - Tool initialization and registration
- `worker/skills/loader.py` (lines 17-71) - Skill parsing from Markdown files
- `worker/config.py` - Configuration management with Pydantic settings

**Database Models:**
- `backend/app/models/task.py` (lines 10-51) - Task and TaskRun models, TaskStatus enum
- `backend/app/models/sandbox.py` (lines 9-23) - SandboxSession model structure
- `backend/app/database.py` (lines 7-36) - Async database engine setup, session factory

**Event Broadcasting:**
- `backend/app/services/event_broadcaster.py` (lines 9-44) - EventBroadcaster class, broadcast() method

**Testing Patterns:**
- `worker/tests/test_agent.py` - Async test patterns with pytest-asyncio
- `worker/tests/test_sandbox_manager.py` - Sandbox testing patterns

### New Files to Create

- `worker/main.py` - Main worker loop entry point
- `worker/tests/test_main.py` - Unit tests for worker main loop

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

**Python Async Programming:**
- [asyncio Event Loop](https://docs.python.org/3/library/asyncio-eventloop.html)
  - Specific section: Running and stopping the loop
  - Why: Core pattern for worker main loop

**SQLAlchemy Async:**
- [SQLAlchemy Async I/O](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - Specific section: AsyncSession usage
  - Why: Database operations in worker

**Structlog:**
- [Structlog Documentation](https://www.structlog.org/en/stable/)
  - Specific section: Processors and context binding
  - Why: Structured logging pattern used throughout project

**Signal Handling:**
- [Python signal module](https://docs.python.org/3/library/signal.html)
  - Specific section: SIGTERM and SIGINT handlers
  - Why: Graceful shutdown implementation

### Patterns to Follow

**Async Database Pattern:**
```python
# From backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session_maker() as session:
        yield session
```

**Logging Pattern:**
```python
# From worker/orchestrator/agent.py
import structlog
logger = structlog.get_logger(__name__)

logger.info("event_name", task_run_id=str(uuid), key=value)
logger.error("error_event", task_run_id=str(uuid), error=str(e))
```

**Agent Execution Pattern:**
```python
# From worker/orchestrator/agent.py (lines 42-52)
agent = Agent(
    task_run_id=run_id,
    model=model_provider,
    tools=tools,
    max_iterations=20,
    skill=skill
)
result = await agent.run(goal=task.goal, system_prompt=system_prompt)
```

**Sandbox Context Manager Pattern:**
```python
# From worker/sandbox/manager.py (lines 47-55)
async with SandboxManager(task_run_id=run_id, image="badgers-sandbox:latest") as sandbox:
    container_id = sandbox.container_id
    # Use sandbox
    # Automatic cleanup on exit
```

**Error Handling Pattern:**
```python
# From worker/orchestrator/agent.py (lines 96-98)
try:
    # Operation
except Exception as e:
    logger.error("operation_failed", task_run_id=str(task_run_id), error=str(e))
    raise SpecificError(f"Context: {e}")
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation Setup

Create the basic worker structure with configuration, logging, and database connection.

**Tasks:**
- Set up async event loop and signal handlers
- Configure structlog with worker-specific context
- Establish database connection using existing patterns
- Create graceful shutdown mechanism

### Phase 2: Task Polling & Retrieval

Implement the mechanism to discover and claim pending tasks.

**Tasks:**
- Query database for PENDING TaskRuns
- Implement task claiming logic (update status to RUNNING)
- Add polling loop with configurable interval
- Handle concurrent worker scenarios (optimistic locking)

### Phase 3: Sandbox & Agent Integration

Integrate sandbox creation and agent execution.

**Tasks:**
- Create SandboxManager for each TaskRun
- Persist SandboxSession to database
- Initialize tools and model provider
- Load skill if specified
- Execute Agent.run() with proper error handling

### Phase 4: Event Broadcasting & Status Updates

Add real-time progress updates and status persistence.

**Tasks:**
- Integrate EventBroadcaster for WebSocket events
- Emit sandbox_created, iteration_start, tool_call events
- Update TaskRun status transitions
- Persist final results and error messages

### Phase 5: Cleanup & Error Recovery

Ensure proper resource cleanup and error handling.

**Tasks:**
- Implement sandbox cleanup (stop and remove containers)
- Handle Agent execution failures gracefully
- Update TaskRun with error details on failure
- Ensure cleanup happens even on exceptions

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE worker/main.py - Main entry point

- **IMPLEMENT**: Import statements and module setup
- **IMPORTS**:
  ```python
  import asyncio
  import signal
  import sys
  import uuid
  from datetime import datetime
  import structlog
  from sqlalchemy import select, update
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

  from config import settings
  from orchestrator.agent import Agent
  from sandbox.manager import SandboxManager
  from models.factory import create_model_provider
  from tools import get_all_tools
  from skills.loader import parse_skill_md
  from skills.registry import get_skill_path
  ```
- **PATTERN**: Mirror import style from `worker/orchestrator/agent.py`
- **VALIDATE**: `python -m py_compile worker/main.py`

### CREATE worker/main.py - Database setup

- **IMPLEMENT**: Database engine and session factory
- **PATTERN**: Copy from `backend/app/database.py` (lines 7-19)
- **CODE**:
  ```python
  # Database setup
  engine = create_async_engine(
      settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
      echo=False,
      pool_pre_ping=True,
  )

  async_session_maker = async_sessionmaker(
      engine,
      class_=AsyncSession,
      expire_on_commit=False,
  )
  ```
- **GOTCHA**: Must replace `postgresql://` with `postgresql+asyncpg://` for async driver
- **VALIDATE**: `python -c "from worker.main import engine; print('DB setup OK')"`

### CREATE worker/main.py - Logging configuration

- **IMPLEMENT**: Configure structlog for worker process
- **PATTERN**: Follow logging style from `worker/orchestrator/agent.py` (line 12)
- **CODE**:
  ```python
  logger = structlog.get_logger(__name__)

  def configure_logging():
      structlog.configure(
          processors=[
              structlog.processors.add_log_level,
              structlog.processors.TimeStamper(fmt="iso"),
              structlog.dev.ConsoleRenderer()
          ],
          wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
          context_class=dict,
          logger_factory=structlog.PrintLoggerFactory(),
      )
  ```
- **VALIDATE**: `python -c "from worker.main import configure_logging; configure_logging(); print('Logging OK')"`

### CREATE worker/main.py - Graceful shutdown handler

- **IMPLEMENT**: Signal handler for SIGTERM and SIGINT
- **PATTERN**: Standard Python signal handling
- **CODE**:
  ```python
  shutdown_event = asyncio.Event()

  def signal_handler(signum, frame):
      logger.info("shutdown_signal_received", signal=signum)
      shutdown_event.set()

  def setup_signal_handlers():
      signal.signal(signal.SIGTERM, signal_handler)
      signal.signal(signal.SIGINT, signal_handler)
  ```
- **VALIDATE**: Manual test with Ctrl+C

### CREATE worker/main.py - Task polling function

- **IMPLEMENT**: Query for PENDING TaskRuns and claim one
- **PATTERN**: Use async SQLAlchemy select from `backend/app/routers/tasks.py`
- **CODE**:
  ```python
  async def get_next_pending_task(session: AsyncSession) -> TaskRun | None:
      """Fetch and claim next PENDING TaskRun."""
      from backend.app.models.task import TaskRun, TaskStatus

      # Query for PENDING tasks
      result = await session.execute(
          select(TaskRun)
          .where(TaskRun.status == TaskStatus.PENDING)
          .order_by(TaskRun.created_at)
          .limit(1)
      )
      task_run = result.scalar_one_or_none()

      if task_run:
          # Claim task by updating status
          task_run.status = TaskStatus.RUNNING
          task_run.started_at = datetime.utcnow()
          await session.commit()
          logger.info("task_claimed", task_run_id=str(task_run.id))

      return task_run
  ```
- **GOTCHA**: Use optimistic locking to prevent race conditions in multi-worker setup
- **VALIDATE**: Unit test with mock database

### CREATE worker/main.py - Task execution function

- **IMPLEMENT**: Core task execution logic with sandbox and agent
- **PATTERN**: Combine patterns from `agent.py` and `sandbox/manager.py`
- **CODE**:
  ```python
  async def execute_task_run(task_run_id: uuid.UUID, session: AsyncSession):
      """Execute a single TaskRun with sandbox and agent."""
      from backend.app.models.task import Task, TaskRun, TaskStatus
      from backend.app.models.sandbox import SandboxSession

      logger = structlog.get_logger().bind(task_run_id=str(task_run_id))
      logger.info("task_execution_started")

      try:
          # Load TaskRun and Task
          result = await session.execute(
              select(TaskRun).where(TaskRun.id == task_run_id)
          )
          task_run = result.scalar_one()

          result = await session.execute(
              select(Task).where(Task.id == task_run.task_id)
          )
          task = result.scalar_one()

          # Create sandbox
          sandbox = SandboxManager(
              task_run_id=task_run_id,
              image=settings.sandbox_image,
              mem_limit=settings.sandbox_memory_limit,
              cpu_quota=settings.sandbox_cpu_quota
          )

          container_id = await sandbox.create()
          logger.info("sandbox_created", container_id=container_id)

          # Persist SandboxSession
          sandbox_session = SandboxSession(
              task_run_id=task_run_id,
              container_id=container_id,
              image=settings.sandbox_image,
              cpu_limit=settings.sandbox_cpu_quota,
              memory_limit=int(settings.sandbox_memory_limit.rstrip('mg'))
          )
          session.add(sandbox_session)
          await session.commit()

          # TODO: Broadcast sandbox_created event

          # Initialize model
          model_provider = create_model_provider(
              provider=settings.model_provider,
              model=task.model or settings.default_main_model,
              config={}
          )

          # Load skill if specified
          skill = None
          if task.skill:
              skill_path = get_skill_path(task.skill)
              skill = parse_skill_md(skill_path)
              logger.info("skill_loaded", skill=task.skill)

          # Initialize tools
          tools = get_all_tools()

          # Create and run agent
          agent = Agent(
              task_run_id=task_run_id,
              model=model_provider,
              tools=tools,
              max_iterations=20,
              skill=skill
          )

          result = await agent.run(
              goal=task.goal,
              system_prompt=skill.system_prompt if skill else None
          )

          # Update TaskRun with success
          task_run.status = TaskStatus.COMPLETED
          task_run.completed_at = datetime.utcnow()
          await session.commit()

          logger.info("task_execution_completed", result_length=len(result))

          # Cleanup sandbox
          await sandbox.destroy()
          sandbox_session.terminated_at = datetime.utcnow()
          await session.commit()

      except Exception as e:
          logger.error("task_execution_failed", error=str(e), exc_info=True)

          # Update TaskRun with failure
          task_run.status = TaskStatus.FAILED
          task_run.completed_at = datetime.utcnow()
          task_run.error_message = str(e)
          await session.commit()

          # Cleanup sandbox if created
          try:
              if 'sandbox' in locals():
                  await sandbox.destroy()
              if 'sandbox_session' in locals():
                  sandbox_session.terminated_at = datetime.utcnow()
                  await session.commit()
          except Exception as cleanup_error:
              logger.error("sandbox_cleanup_failed", error=str(cleanup_error))
  ```
- **GOTCHA**: Ensure sandbox cleanup happens even on exceptions
- **VALIDATE**: Unit test with mocked components

### CREATE worker/main.py - Main worker loop

- **IMPLEMENT**: Continuous polling loop with graceful shutdown
- **PATTERN**: Standard async polling pattern
- **CODE**:
  ```python
  async def worker_loop():
      """Main worker loop - poll for tasks and execute."""
      logger.info("worker_started")

      while not shutdown_event.is_set():
          try:
              async with async_session_maker() as session:
                  task_run = await get_next_pending_task(session)

                  if task_run:
                      await execute_task_run(task_run.id, session)
                  else:
                      # No tasks available, wait before polling again
                      await asyncio.sleep(settings.worker_poll_interval or 5)

          except Exception as e:
              logger.error("worker_loop_error", error=str(e), exc_info=True)
              await asyncio.sleep(5)  # Back off on error

      logger.info("worker_stopped")
  ```
- **VALIDATE**: Integration test with test database

### CREATE worker/main.py - Main entry point

- **IMPLEMENT**: Main function and __main__ block
- **CODE**:
  ```python
  async def main():
      """Main entry point."""
      configure_logging()
      setup_signal_handlers()

      logger.info("worker_initializing")

      try:
          await worker_loop()
      except KeyboardInterrupt:
          logger.info("worker_interrupted")
      finally:
          await engine.dispose()
          logger.info("worker_shutdown_complete")

  if __name__ == "__main__":
      asyncio.run(main())
  ```
- **VALIDATE**: `python -m worker.main` (should start without errors)

### UPDATE worker/config.py - Add worker settings

- **IMPLEMENT**: Add worker-specific configuration
- **ADD**:
  ```python
  # Worker settings
  worker_poll_interval: int = 5  # seconds
  sandbox_image: str = "badgers-sandbox:latest"
  sandbox_memory_limit: str = "512m"
  sandbox_cpu_quota: int = 50000
  ```
- **PATTERN**: Follow existing Pydantic settings pattern
- **VALIDATE**: `python -c "from worker.config import settings; print(settings.worker_poll_interval)"`

### CREATE worker/tests/test_main.py - Unit tests

- **IMPLEMENT**: Test suite for worker main loop
- **PATTERN**: Follow `worker/tests/test_agent.py` async test pattern
- **CODE**:
  ```python
  import pytest
  import uuid
  from unittest.mock import AsyncMock, Mock, patch
  from worker.main import get_next_pending_task, execute_task_run

  @pytest.mark.asyncio
  async def test_get_next_pending_task_returns_none_when_empty():
      mock_session = AsyncMock()
      mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

      result = await get_next_pending_task(mock_session)

      assert result is None

  @pytest.mark.asyncio
  async def test_get_next_pending_task_claims_task():
      from backend.app.models.task import TaskRun, TaskStatus

      mock_task_run = Mock(spec=TaskRun)
      mock_task_run.id = uuid.uuid4()
      mock_task_run.status = TaskStatus.PENDING

      mock_session = AsyncMock()
      mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task_run)))
      mock_session.commit = AsyncMock()

      result = await get_next_pending_task(mock_session)

      assert result == mock_task_run
      assert result.status == TaskStatus.RUNNING
      mock_session.commit.assert_called_once()

  @pytest.mark.asyncio
  async def test_execute_task_run_success():
      # Test successful task execution
      # Mock all dependencies: session, sandbox, agent, model
      pass  # Implement full test

  @pytest.mark.asyncio
  async def test_execute_task_run_failure_updates_status():
      # Test that failures are properly recorded
      pass  # Implement full test
  ```
- **VALIDATE**: `cd worker && uv run pytest tests/test_main.py -v`

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test individual functions in isolation with mocked dependencies

**Test Cases**:
1. `test_get_next_pending_task_returns_none_when_empty` - Verify no task returns None
2. `test_get_next_pending_task_claims_task` - Verify task status updated to RUNNING
3. `test_execute_task_run_success` - Mock full execution, verify COMPLETED status
4. `test_execute_task_run_failure_updates_status` - Simulate error, verify FAILED status
5. `test_execute_task_run_cleans_up_sandbox` - Verify sandbox.destroy() called
6. `test_signal_handler_sets_shutdown_event` - Verify graceful shutdown trigger

**Fixtures**:
```python
@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_task_run():
    from backend.app.models.task import TaskRun, TaskStatus
    task_run = Mock(spec=TaskRun)
    task_run.id = uuid.uuid4()
    task_run.status = TaskStatus.PENDING
    return task_run
```

### Integration Tests

**Scope**: Test worker with real database (test DB) and mocked external services

**Test Cases**:
1. End-to-end task execution with test database
2. Multiple tasks processed sequentially
3. Graceful shutdown with in-flight task
4. Database connection recovery after failure

**Setup**:
- Use pytest fixtures to create test database
- Seed with test TaskRun records
- Mock Agent execution to avoid real LLM calls
- Mock Docker to avoid real container creation

### Edge Cases

1. **Concurrent Workers**: Two workers claim different tasks (no collision)
2. **Task Already Running**: Worker skips task that another worker claimed
3. **Database Connection Loss**: Worker reconnects and continues
4. **Sandbox Creation Failure**: Task marked FAILED, no orphan containers
5. **Agent Timeout**: Task fails gracefully after max iterations
6. **Shutdown During Execution**: Current task completes before shutdown

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Check syntax
python -m py_compile worker/main.py

# Run linter (if ruff is configured)
cd worker && ruff check main.py
```

### Level 2: Unit Tests

```bash
# Run worker tests
cd worker && uv run pytest tests/test_main.py -v

# Run with coverage
cd worker && uv run pytest tests/test_main.py --cov=worker.main --cov-report=term
```

### Level 3: Integration Tests

```bash
# Run all worker tests
cd worker && uv run pytest tests/ -v

# Test database connectivity
python -c "from worker.main import engine; import asyncio; asyncio.run(engine.dispose()); print('DB OK')"
```

### Level 4: Manual Validation

**Start Worker Process**:
```bash
cd worker
uv run python -m worker.main
```

**Expected Output**:
```
worker_initializing
worker_started
```

**Create Test Task** (in another terminal):
```bash
# Use backend API to create a test task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "...", "project_id": "...", "goal": "test task"}'

# Create TaskRun
curl -X POST http://localhost:8000/api/tasks/{task_id}/runs
```

**Verify Execution**:
- Check worker logs for `task_claimed`, `sandbox_created`, `task_execution_completed`
- Query database: `SELECT status FROM task_runs WHERE id = '...'` should show COMPLETED
- Verify SandboxSession record created and terminated_at set

**Test Graceful Shutdown**:
```bash
# Send SIGTERM
kill -TERM <worker_pid>

# Verify logs show:
# shutdown_signal_received
# worker_stopped
# worker_shutdown_complete
```

---

## ACCEPTANCE CRITERIA

- [ ] Worker process starts successfully and enters polling loop
- [ ] Worker discovers PENDING TaskRuns from database
- [ ] TaskRun status transitions: PENDING → RUNNING → COMPLETED/FAILED
- [ ] SandboxSession record created with container_id
- [ ] Agent executes with correct model, tools, and skill
- [ ] Sandbox cleanup occurs on both success and failure
- [ ] Worker handles SIGTERM/SIGINT gracefully
- [ ] All unit tests pass with >80% coverage
- [ ] Integration test completes end-to-end task execution
- [ ] No database connection leaks (verified with connection pool monitoring)
- [ ] Structured logs include task_run_id context
- [ ] Worker can process multiple tasks sequentially

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] worker/main.py created with all functions
- [ ] worker/config.py updated with worker settings
- [ ] worker/tests/test_main.py created with test suite
- [ ] All validation commands executed successfully
- [ ] Unit tests pass (pytest)
- [ ] Manual testing confirms task execution
- [ ] Graceful shutdown tested
- [ ] Code follows project conventions (async/await, structlog)
- [ ] No linting errors

---

## NOTES

**Design Decisions**:

1. **Database Polling vs Redis Queue**: Initial implementation uses database polling for simplicity. Redis queue can be added later for better scalability.

2. **Single Task Execution**: Worker processes one task at a time. Multi-task concurrency can be added in future iterations.

3. **Event Broadcasting**: Initial implementation logs events but doesn't broadcast to WebSocket. Integration with `EventBroadcaster` requires shared state or Redis pub/sub.

4. **Error Recovery**: Worker continues on errors rather than crashing. Individual task failures don't stop the worker.

5. **Sandbox Image**: Assumes `badgers-sandbox:latest` image exists. Must be built from `docker/sandbox-base/Dockerfile`.

**Future Enhancements**:

- Redis queue integration for task distribution
- WebSocket event broadcasting integration
- Concurrent task execution (asyncio.gather)
- Health check endpoint
- Metrics collection (Prometheus)
- Task priority queue
- Worker pool management

**Known Limitations**:

- No distributed locking (race condition possible with multiple workers)
- No task timeout enforcement (relies on Agent max_iterations)
- No retry logic for transient failures
- Event broadcasting not implemented (requires architecture decision)
