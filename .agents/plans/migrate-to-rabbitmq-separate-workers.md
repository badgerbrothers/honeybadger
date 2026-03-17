# Feature: Migrate Task Scheduling from Database Polling to RabbitMQ with Specialized Workers

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Migrate the current database polling task scheduler to a RabbitMQ-based message queue system with two specialized worker types: one for TaskRun execution (agent tasks with Docker sandboxes) and one for DocumentIndexJob execution (file parsing and embedding). This improves response latency from 5 seconds to milliseconds, enables horizontal scaling of workers, reduces database load, and allows independent scaling of different worker types based on workload.

## User Story

As a system administrator
I want to use RabbitMQ for task distribution with specialized workers
So that I can scale TaskRun and IndexJob workers independently, reduce task response latency, and eliminate database polling overhead

## Problem Statement

The current system uses database polling where workers query the database every 5 seconds for pending tasks:
- High response latency (5 second polling interval)
- Database pressure increases linearly with worker count
- Cannot independently scale different task types (TaskRun vs DocumentIndexJob)
- Resource waste from empty polling cycles
- TaskRun workers (heavy, need Docker) and IndexJob workers (lightweight) have same configuration

## Solution Statement

Implement RabbitMQ message queue with two separate queues (`task-runs` and `index-jobs`) and two specialized worker types that consume from their respective queues. Backend pushes tasks to appropriate queues upon creation. Workers use aio-pika for async consumption with automatic task distribution and acknowledgment.

## Feature Metadata

**Feature Type**: Enhancement/Refactor
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Worker task scheduling loop
- Backend task creation endpoints
- Docker Compose infrastructure
- Configuration management

**Dependencies**:
- RabbitMQ 3.x (with management plugin)
- aio-pika >= 9.0.0 (Python async RabbitMQ client)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/main.py` (lines 89-127, 287-470, 494-517) - Why: Current polling logic and task execution functions to preserve
- `worker/config.py` (lines 1-59) - Why: Configuration pattern to follow for RabbitMQ settings
- `backend/app/config.py` (lines 1-47) - Why: Backend configuration pattern
- `backend/app/routers/tasks.py` (lines 69-81) - Why: TaskRun creation endpoint to modify
- `backend/app/routers/projects.py` (lines 114-120) - Why: DocumentIndexJob scheduling to modify
- `backend/app/services/rag_service.py` (lines 18-37) - Why: IndexJob creation pattern
- `docker-compose.yml` (lines 78-108) - Why: Current worker service configuration
- `.env.example` (all) - Why: Environment variable patterns

### New Files to Create

- `worker/queueing/rabbitmq_client.py` - RabbitMQ connection and queue management
- `backend/app/services/queue_service.py` - Backend queue publishing service
- `worker/worker_taskrun.py` - Specialized TaskRun worker entry point
- `worker/worker_indexjob.py` - Specialized IndexJob worker entry point

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [aio-pika Documentation](https://aio-pika.readthedocs.io/en/latest/)
  - Specific section: Getting Started, Robust Connection
  - Why: Required for implementing async RabbitMQ consumers and producers
- [RabbitMQ Tutorials](https://www.rabbitmq.com/tutorials/tutorial-one-python.html)
  - Specific section: Work Queues (Tutorial 2)
  - Why: Understanding work queue pattern and message acknowledgment
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
  - Why: Alternative pattern for non-blocking queue publishing

### Patterns to Follow

**Configuration Pattern** (from `worker/config.py` and `backend/app/config.py`):
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Use descriptive names with defaults
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"
```

**Async Database Session Pattern** (from `worker/main.py:500`):
```python
async with async_session_maker() as session:
    # perform database operations
    await session.commit()
```

**Logging Pattern** (from `worker/main.py:34-48`):
```python
import structlog
logger = structlog.get_logger(__name__)
logger.info("event_name", key1=value1, key2=value2)
```

**Error Handling Pattern** (from `worker/main.py:440-469`):
```python
try:
    # operation
except Exception as e:
    logger.error("operation_failed", error=str(e), exc_info=True)
    # cleanup
```

**Docker Compose Service Pattern** (from `docker-compose.yml:78-108`):
```yaml
service_name:
  build:
    context: .
    dockerfile: path/Dockerfile
  environment:
    VAR_NAME: ${VAR_NAME:-default}
  depends_on:
    other_service:
      condition: service_healthy
```

---

## IMPLEMENTATION PLAN

### Phase 1: Infrastructure Setup

Add RabbitMQ service to Docker Compose and configure environment variables for both backend and worker.

**Tasks:**
- Add RabbitMQ service with management UI
- Add RabbitMQ configuration to backend and worker settings
- Update environment variable examples

### Phase 2: Queue Client Implementation

Create RabbitMQ client utilities for connection management, queue declaration, message publishing, and consumption.

**Tasks:**
- Implement robust connection management with aio-pika
- Create queue declaration and binding logic
- Implement message publishing with error handling
- Implement message consumption with acknowledgment

### Phase 3: Backend Integration

Modify backend endpoints to publish messages to RabbitMQ queues instead of relying on database polling.

**Tasks:**
- Create queue service for backend
- Modify TaskRun creation endpoint
- Modify DocumentIndexJob scheduling
- Add queue service initialization to FastAPI startup

### Phase 4: Worker Specialization

Create two specialized worker entry points that consume from specific queues and execute appropriate task types.

**Tasks:**
- Create TaskRun worker entry point
- Create IndexJob worker entry point
- Preserve existing execution logic
- Add graceful shutdown handling

### Phase 5: Docker Compose Configuration

Update Docker Compose to run two separate worker services with appropriate configurations and resource allocations.

**Tasks:**
- Configure worker-taskrun service
- Configure worker-indexjob service
- Set appropriate resource limits
- Configure dependencies and health checks

### Phase 6: Testing & Validation

Verify the complete flow works correctly with multiple workers and proper task distribution.

**Tasks:**
- Test single worker of each type
- Test multiple workers of each type
- Verify task distribution and acknowledgment
- Test failure scenarios and retries

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: UPDATE docker-compose.yml

- **ADD**: RabbitMQ service with management plugin
- **PATTERN**: Follow existing service structure (postgres, redis, minio)
- **IMPLEMENTATION**:
  ```yaml
  rabbitmq:
    image: rabbitmq:3-management
    container_name: badgers-rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-admin}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-password}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 10
  ```
- **ADD**: Volume for RabbitMQ data persistence in volumes section
- **GOTCHA**: Place after minio service, before backend service
- **VALIDATE**: `docker compose config` (validates YAML syntax)

### Task 2: UPDATE .env.example

- **ADD**: RabbitMQ configuration variables
- **PATTERN**: Follow existing service configuration format (lines 1-16)
- **IMPLEMENTATION**:
  ```
  # RabbitMQ
  RABBITMQ_HOST=localhost
  RABBITMQ_PORT=5672
  RABBITMQ_USER=admin
  RABBITMQ_PASSWORD=password
  RABBITMQ_MANAGEMENT_PORT=15672
  ```
- **GOTCHA**: Add after Redis section, before Object Storage section
- **VALIDATE**: Visual inspection of file structure

### Task 3: UPDATE backend/app/config.py

- **ADD**: RabbitMQ settings to Settings class
- **PATTERN**: Mirror redis_url pattern (line 13)
- **IMPLEMENTATION**:
  ```python
  # RabbitMQ
  rabbitmq_host: str = "localhost"
  rabbitmq_port: int = 5672
  rabbitmq_user: str = "admin"
  rabbitmq_password: str = "password"

  @property
  def rabbitmq_url(self) -> str:
      return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"
  ```
- **GOTCHA**: Add after redis_url (line 13), before openai_api_key
- **VALIDATE**: `cd backend && uv run python -c "from app.config import settings; print(settings.rabbitmq_url)"`

### Task 4: UPDATE worker/config.py

- **ADD**: RabbitMQ settings to Settings class
- **PATTERN**: Mirror backend/app/config.py RabbitMQ settings
- **IMPLEMENTATION**: Same as Task 3
- **GOTCHA**: Add after redis_url (line 13), before model_provider
- **VALIDATE**: `cd worker && uv run python -c "from config import settings; print(settings.rabbitmq_url)"`

### Task 5: UPDATE backend/pyproject.toml

- **ADD**: aio-pika dependency
- **PATTERN**: Follow existing dependency format (lines 6-23)
- **IMPLEMENTATION**: Add `"aio-pika>=9.0.0",` to dependencies list
- **GOTCHA**: Add after httpx, before python-multipart
- **VALIDATE**: `cd backend && uv sync && uv run python -c "import aio_pika; print(aio_pika.__version__)"`

### Task 6: UPDATE worker/pyproject.toml

- **ADD**: aio-pika dependency
- **PATTERN**: Follow existing dependency format (lines 6-27)
- **IMPLEMENTATION**: Add `"aio-pika>=9.0.0",` to dependencies list
- **GOTCHA**: Add after httpx, before minio
- **VALIDATE**: `cd worker && uv sync && uv run python -c "import aio_pika; print(aio_pika.__version__)"`

### Task 7: CREATE worker/queueing/rabbitmq_client.py

- **CREATE**: RabbitMQ client for worker-side queue operations
- **PATTERN**: Use structlog logging (worker/main.py:34), async context managers
- **IMPORTS**: `import aio_pika, structlog, asyncio, json, uuid`
- **IMPLEMENTATION**:
  ```python
  """RabbitMQ client for task queue operations."""
  import json
  import uuid
  import structlog
  import aio_pika
  from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection, AbstractRobustChannel, AbstractQueue
  from config import settings

  logger = structlog.get_logger(__name__)

  class RabbitMQClient:
      """Async RabbitMQ client with robust connection."""

      def __init__(self, queue_name: str):
          self.queue_name = queue_name
          self.connection: AbstractRobustConnection | None = None
          self.channel: AbstractRobustChannel | None = None
          self.queue: AbstractQueue | None = None

      async def connect(self):
          """Establish connection and declare queue."""
          self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
          self.channel = await self.connection.channel()
          await self.channel.set_qos(prefetch_count=1)
          self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
          logger.info("rabbitmq_connected", queue=self.queue_name)

      async def consume(self, callback, stop_event: asyncio.Event | None = None):
          """Consume messages from queue with explicit ack/nack behavior."""
          async with self.queue.iterator() as queue_iter:
              async for message in queue_iter:
                  if stop_event and stop_event.is_set():
                      break
                  await self._handle_message(message, callback)

      async def _handle_message(self, message: AbstractIncomingMessage, callback):
          """Decode and process a message with deterministic ack/nack."""
          try:
              data = json.loads(message.body.decode())
          except Exception as exc:
              logger.error("rabbitmq_decode_failed", queue=self.queue_name, error=str(exc))
              await message.ack()
              return

          try:
              await callback(data)
              await message.ack()
          except ValueError as exc:
              # Payload/business validation error: don't poison the queue with infinite retry.
              logger.error("rabbitmq_message_rejected", queue=self.queue_name, error=str(exc))
              await message.reject(requeue=False)
          except Exception as exc:
              logger.error("rabbitmq_message_failed", queue=self.queue_name, error=str(exc), exc_info=True)
              await message.nack(requeue=True)

      async def close(self):
          """Close connection."""
          if self.connection:
              await self.connection.close()
              logger.info("rabbitmq_closed", queue=self.queue_name)
  ```
- **GOTCHA**:
  - Must use `connect_robust` for auto-reconnection
  - Must use `durable=True` for queue persistence
  - Use explicit `ack()/nack()/reject()` (don't rely on default `message.process()` behavior)
- **VALIDATE**: `cd worker && uv run python -c "from worker.queueing.rabbitmq_client import RabbitMQClient; print('OK')"`

### Task 8: CREATE backend/app/services/queue_service.py

- **CREATE**: Queue service for backend to publish tasks
- **PATTERN**: Follow storage_service pattern (backend/app/services/storage.py structure)
- **IMPORTS**: `import aio_pika, structlog, json, uuid`
- **IMPLEMENTATION**:
  ```python
  """Queue service for publishing tasks to RabbitMQ."""
  import json
  import uuid
  import structlog
  import aio_pika
  from aio_pika import Message, DeliveryMode
  from app.config import settings

  logger = structlog.get_logger(__name__)

  class QueueService:
      """RabbitMQ publisher for task distribution."""

      def __init__(self):
          self.connection = None
          self.channel = None

      async def connect(self):
          """Initialize RabbitMQ connection."""
          self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
          self.channel = await self.connection.channel()
          await self.channel.declare_queue("task-runs", durable=True)
          await self.channel.declare_queue("index-jobs", durable=True)
          logger.info("queue_service_connected")

      async def publish_task_run(self, task_run_id: uuid.UUID):
          """Publish TaskRun to task-runs queue."""
          message = Message(
              body=json.dumps({"task_run_id": str(task_run_id)}).encode(),
              delivery_mode=DeliveryMode.PERSISTENT
          )
          await self.channel.default_exchange.publish(
              message, routing_key="task-runs"
          )
          logger.info("task_run_published", task_run_id=str(task_run_id))

      async def publish_index_job(self, job_id: uuid.UUID):
          """Publish DocumentIndexJob to index-jobs queue."""
          message = Message(
              body=json.dumps({"job_id": str(job_id)}).encode(),
              delivery_mode=DeliveryMode.PERSISTENT
          )
          await self.channel.default_exchange.publish(
              message, routing_key="index-jobs"
          )
          logger.info("index_job_published", job_id=str(job_id))

      async def close(self):
          """Close connection."""
          if self.connection:
              await self.connection.close()

  queue_service = QueueService()
  ```
- **GOTCHA**:
  - Use `DeliveryMode.PERSISTENT` for message durability
  - Declare queues in publisher startup to avoid publish-before-consumer message loss
- **VALIDATE**: `cd backend && uv run python -c "from app.services.queue_service import queue_service; print('OK')"`

### Task 9: UPDATE backend/app/main.py

- **ADD**: Queue service initialization on startup
- **PATTERN**: Follow existing startup pattern if present
- **IMPORTS**: Add `from app.services.queue_service import queue_service`
- **IMPLEMENTATION**:
  ```python
  @app.on_event("startup")
  async def startup_event():
      await queue_service.connect()

  @app.on_event("shutdown")
  async def shutdown_event():
      await queue_service.close()
  ```
- **GOTCHA**: Add after app initialization (line 6), before middleware
- **VALIDATE**: `cd backend && uv run python -c "from app.main import app; print('OK')"`

### Task 10: UPDATE backend/app/routers/tasks.py

- **MODIFY**: create_task_run endpoint to publish to RabbitMQ
- **PATTERN**: Keep existing database logic, add queue publish after commit
- **IMPORTS**: Add `from app.services.queue_service import queue_service`
- **IMPLEMENTATION**: In create_task_run function (lines 69-81), after `await db.refresh(db_run)`:
  ```python
  # Publish to RabbitMQ queue
  try:
      await queue_service.publish_task_run(db_run.id)
  except Exception:
      # Compensating update: leave task visible with explicit queue failure signal.
      db_run.status = TaskStatus.FAILED
      db_run.error_message = "queue_publish_failed"
      task.current_run_id = None
      await db.commit()
      raise HTTPException(status_code=503, detail="Task queued failed")
  ```
- **GOTCHA**:
  - Publish AFTER db.commit() to ensure task exists in database
  - Add compensating logic for publish failure (avoid orphaned pending runs)
- **VALIDATE**: `cd backend && uv run python -c "from app.routers.tasks import router; print('OK')"`

### Task 11: UPDATE backend/app/services/rag_service.py

- **MODIFY**: schedule_indexing method to publish to RabbitMQ
- **PATTERN**: Keep existing database logic, add queue publish after commit
- **IMPORTS**: Add `from app.services.queue_service import queue_service` at top
- **IMPLEMENTATION**: In schedule_indexing method (lines 18-37), after `await db.refresh(job)`:
  ```python
  # Publish to RabbitMQ queue
  try:
      await queue_service.publish_index_job(job.id)
  except Exception:
      job.status = DocumentIndexStatus.FAILED
      job.error_message = "queue_publish_failed"
      await db.commit()
      raise
  ```
- **GOTCHA**:
  - Publish AFTER db.commit() and db.refresh()
  - Add compensating logic for publish failure (avoid orphaned pending index jobs)
- **VALIDATE**: `cd backend && uv run python -c "from app.services.rag_service import rag_service; print('OK')"`

### Task 12: CREATE worker/worker_taskrun.py

- **CREATE**: Specialized worker for TaskRun execution
- **PATTERN**: Mirror worker/main.py structure (lines 494-533)
- **IMPORTS**: Reuse from worker/main.py
- **IMPLEMENTATION**:
  ```python
  """TaskRun specialized worker."""
  import asyncio
  import uuid
  import signal
  import structlog
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
  from config import settings
  from worker.main import execute_task_run, configure_logging, engine, async_session_maker
  from worker.queueing.rabbitmq_client import RabbitMQClient

  logger = structlog.get_logger(__name__)
  shutdown_event = asyncio.Event()

  def signal_handler(signum, frame):
      logger.info("shutdown_signal_received", signal=signum)
      shutdown_event.set()

  async def handle_task_run(data: dict):
      """Handle TaskRun message."""
      task_run_id = uuid.UUID(data["task_run_id"])
      logger.info("task_run_received", task_run_id=str(task_run_id))
      async with async_session_maker() as session:
          await execute_task_run(task_run_id, session)

  async def main():
      configure_logging()
      signal.signal(signal.SIGTERM, signal_handler)
      signal.signal(signal.SIGINT, signal_handler)

      logger.info("taskrun_worker_starting")
      client = RabbitMQClient("task-runs")
      await client.connect()

      try:
          consume_task = asyncio.create_task(client.consume(handle_task_run, stop_event=shutdown_event))
          await shutdown_event.wait()
          consume_task.cancel()
          await asyncio.gather(consume_task, return_exceptions=True)
      except asyncio.CancelledError:
          logger.info("taskrun_worker_cancelled")
      finally:
          await client.close()
          await engine.dispose()
          logger.info("taskrun_worker_stopped")

  if __name__ == "__main__":
      asyncio.run(main())
  ```
- **GOTCHA**: Reuse execute_task_run from main.py, don't duplicate
- **VALIDATE**: `cd worker && uv run python -c "from worker.worker_taskrun import main; print('OK')"`

### Task 13: CREATE worker/worker_indexjob.py

- **CREATE**: Specialized worker for DocumentIndexJob execution
- **PATTERN**: Mirror worker_taskrun.py structure
- **IMPORTS**: Same as worker_taskrun.py
- **IMPLEMENTATION**:
  ```python
  """DocumentIndexJob specialized worker."""
  import asyncio
  import uuid
  import signal
  import structlog
  from config import settings
  from worker.main import execute_document_index_job, configure_logging, engine, async_session_maker
  from worker.queueing.rabbitmq_client import RabbitMQClient

  logger = structlog.get_logger(__name__)
  shutdown_event = asyncio.Event()

  def signal_handler(signum, frame):
      logger.info("shutdown_signal_received", signal=signum)
      shutdown_event.set()

  async def handle_index_job(data: dict):
      """Handle DocumentIndexJob message."""
      job_id = uuid.UUID(data["job_id"])
      logger.info("index_job_received", job_id=str(job_id))
      async with async_session_maker() as session:
          await execute_document_index_job(job_id, session)

  async def main():
      configure_logging()
      signal.signal(signal.SIGTERM, signal_handler)
      signal.signal(signal.SIGINT, signal_handler)

      logger.info("indexjob_worker_starting")
      client = RabbitMQClient("index-jobs")
      await client.connect()

      try:
          consume_task = asyncio.create_task(client.consume(handle_index_job, stop_event=shutdown_event))
          await shutdown_event.wait()
          consume_task.cancel()
          await asyncio.gather(consume_task, return_exceptions=True)
      except asyncio.CancelledError:
          logger.info("indexjob_worker_cancelled")
      finally:
          await client.close()
          await engine.dispose()
          logger.info("indexjob_worker_stopped")

  if __name__ == "__main__":
      asyncio.run(main())
  ```
- **GOTCHA**: Reuse execute_document_index_job from main.py
- **VALIDATE**: `cd worker && uv run python -c "from worker.worker_indexjob import main; print('OK')"`

### Task 14: UPDATE docker-compose.yml - Add RabbitMQ dependency to backend

- **MODIFY**: backend service depends_on section
- **PATTERN**: Follow existing depends_on structure (lines 65-71)
- **IMPLEMENTATION**: Add to backend depends_on:
  ```yaml
  rabbitmq:
    condition: service_healthy
  ```
- **GOTCHA**: Add after minio, before healthcheck
- **VALIDATE**: `docker compose config`

### Task 15: UPDATE docker-compose.yml - Replace worker with worker-taskrun

- **MODIFY**: Rename worker service to worker-taskrun
- **PATTERN**: Keep existing configuration (lines 78-108)
- **IMPLEMENTATION**: Change service name from `worker:` to `worker-taskrun:` and update command:
  ```yaml
  command: uv run --project /app/worker python -m worker.worker_taskrun
  ```
- **ADD**: Environment variable `WORKER_TYPE: taskrun`
- **MODIFY**: depends_on to include rabbitmq with service_healthy condition
- **GOTCHA**: Keep Docker socket mount for sandbox creation
- **VALIDATE**: `docker compose config`

### Task 16: ADD docker-compose.yml - Create worker-indexjob service

- **CREATE**: New worker-indexjob service
- **PATTERN**: Copy worker-taskrun structure, modify for indexjob
- **IMPLEMENTATION**:
  ```yaml
  worker-indexjob:
    build:
      context: .
      dockerfile: worker/Dockerfile
    working_dir: /app
    command: uv run --project /app/worker python -m worker.worker_indexjob
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-badgers}:${POSTGRES_PASSWORD:-badgers_dev_password}@postgres:5432/${POSTGRES_DB:-badgers}
      REDIS_URL: redis://redis:6379/0
      BACKEND_BASE_URL: http://backend:8000
      S3_ENDPOINT: minio:9000
      S3_ACCESS_KEY: ${S3_ACCESS_KEY:-badgers}
      S3_SECRET_KEY: ${S3_SECRET_KEY:-badgers_dev_password}
      S3_BUCKET: ${S3_BUCKET:-badgers-artifacts}
      S3_SECURE: "false"
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      OPENAI_BASE_URL: ${OPENAI_BASE_URL:-https://api.openai.com/v1}
      RABBITMQ_HOST: rabbitmq
      RABBITMQ_PORT: 5672
      RABBITMQ_USER: ${RABBITMQ_USER:-admin}
      RABBITMQ_PASSWORD: ${RABBITMQ_PASSWORD:-password}
      WORKER_TYPE: indexjob
    volumes:
      - ./:/app
    depends_on:
      backend:
        condition: service_healthy
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
  ```
- **GOTCHA**: NO Docker socket mount (indexjob doesn't need sandboxes)
- **VALIDATE**: `docker compose config`

### Task 17: UPDATE docker-compose.yml - Add RabbitMQ environment to backend

- **ADD**: RabbitMQ environment variables to backend service
- **PATTERN**: Follow existing environment variable format (lines 50-60)
- **IMPLEMENTATION**: Add to backend environment section:
  ```yaml
  RABBITMQ_HOST: rabbitmq
  RABBITMQ_PORT: 5672
  RABBITMQ_USER: ${RABBITMQ_USER:-admin}
  RABBITMQ_PASSWORD: ${RABBITMQ_PASSWORD:-password}
  ```
- **GOTCHA**: Use service name `rabbitmq` as host (not localhost)
- **VALIDATE**: `docker compose config`

### Task 18: UPDATE docker-compose.yml - Add RabbitMQ environment to worker-taskrun

- **ADD**: RabbitMQ environment variables to worker-taskrun service
- **PATTERN**: Same as Task 17
- **IMPLEMENTATION**: Add same RabbitMQ environment variables
- **VALIDATE**: `docker compose config`

### Task 19: CREATE worker/queueing/__init__.py

- **CREATE**: Empty init file for queueing package
- **IMPLEMENTATION**: Empty file or `"""Queue utilities."""`
- **VALIDATE**: `cd worker && uv run python -c "from worker.queueing import rabbitmq_client; print('OK')"`

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test queue client and service in isolation

**Test Files to Create**:
- `backend/tests/test_queue_service.py` - Test message publishing
- `worker/tests/test_rabbitmq_client.py` - Test message consumption

**Key Test Cases**:
- Queue connection establishment
- Message publishing with correct format
- Message consumption and acknowledgment
- Connection failure and retry
- Graceful shutdown

### Integration Tests

**Scope**: End-to-end task flow through RabbitMQ

**Test Scenarios**:
1. Create TaskRun via API → Verify published to queue → Verify worker consumes
2. Upload file → Verify IndexJob published → Verify indexjob worker consumes
3. Multiple workers consume from same queue without duplication
4. Worker failure → Message requeued → Another worker picks up

### Edge Cases

- RabbitMQ service down during task creation (should fail gracefully)
- Worker crashes mid-execution (message should be requeued)
- Malformed message in queue (should log error and acknowledge)
- Queue full scenario (should handle backpressure)
- Network partition between worker and RabbitMQ

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Backend linting
cd backend && uv run ruff check app/

# Worker linting
cd worker && uv run ruff check .

# Docker Compose validation
docker compose config
```

### Level 2: Dependency Installation

```bash
# Backend dependencies
cd backend && uv sync && uv run python -c "import aio_pika; print('aio-pika installed')"

# Worker dependencies
cd worker && uv sync && uv run python -c "import aio_pika; print('aio-pika installed')"
```

### Level 3: Import Validation

```bash
# Backend imports
cd backend && uv run python -c "from app.services.queue_service import queue_service; print('Backend queue service OK')"

# Worker imports
cd worker && uv run python -c "from worker.queueing.rabbitmq_client import RabbitMQClient; print('Worker queue client OK')"
cd worker && uv run python -c "from worker.worker_taskrun import main; print('TaskRun worker OK')"
cd worker && uv run python -c "from worker.worker_indexjob import main; print('IndexJob worker OK')"
```

### Level 4: Service Startup

```bash
# Start infrastructure
docker compose up -d postgres redis minio rabbitmq

# Wait for health checks
sleep 10

# Verify RabbitMQ is running
curl -u admin:password http://localhost:15672/api/overview

# Start backend
cd backend && uv run uvicorn app.main:app --reload &

# Start workers
cd worker && uv run python -m worker.worker_taskrun &
cd worker && uv run python -m worker.worker_indexjob &
```

### Level 5: End-to-End Manual Testing

```bash
# Test 1: Create TaskRun
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "UUID", "project_id": "UUID", "goal": "test task"}'

# Get task ID from response, then create run
curl -X POST http://localhost:8000/api/tasks/{task_id}/runs

# Verify worker logs show task execution

# Test 2: Upload file (triggers IndexJob)
curl -X POST http://localhost:8000/api/projects/{project_id}/files/upload \
  -F "file=@test.txt"

# Verify indexjob worker logs show indexing execution

# Test 3: Check RabbitMQ management UI
# Open http://localhost:15672 (admin/password)
# Verify queues "task-runs" and "index-jobs" exist
# Check message rates and consumer counts
```

### Level 6: Multi-Worker Scaling Test

```bash
# Scale workers using Docker Compose
docker compose up -d --scale worker-taskrun=3 --scale worker-indexjob=2

# Create multiple tasks rapidly
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/tasks/{task_id}/runs
done

# Verify in RabbitMQ UI that tasks are distributed across workers
# Check worker logs to confirm different workers processing different tasks
```

---

## ACCEPTANCE CRITERIA

- [ ] RabbitMQ service starts successfully in Docker Compose
- [ ] Backend publishes TaskRun messages to "task-runs" queue
- [ ] Backend publishes IndexJob messages to "index-jobs" queue
- [ ] TaskRun worker consumes from "task-runs" queue and executes tasks
- [ ] IndexJob worker consumes from "index-jobs" queue and executes indexing
- [ ] Multiple workers of same type can run concurrently without conflicts
- [ ] Task execution logic remains unchanged (execute_task_run, execute_document_index_job)
- [ ] All validation commands pass with zero errors
- [ ] RabbitMQ management UI shows both queues with active consumers
- [ ] Task response latency reduced from 5s to <100ms
- [ ] Database polling loop removed from worker/main.py (or deprecated)
- [ ] Workers handle graceful shutdown (SIGTERM/SIGINT)
- [ ] Messages are persistent (queue durable + delivery_mode persistent)
- [ ] Requeue behavior is explicit (nack requeue on transient errors, reject on invalid payload)

---

## COMPLETION CHECKLIST

- [ ] All 19 tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All Level 1-6 validation commands executed successfully
- [ ] RabbitMQ service healthy in docker compose ps
- [ ] Backend starts without errors
- [ ] Both worker types start without errors
- [ ] Manual end-to-end test successful
- [ ] Multi-worker scaling test successful
- [ ] No regressions in existing functionality
- [ ] Code follows project conventions (structlog, async patterns)
- [ ] Acceptance criteria all met

---

## NOTES

### Design Decisions

**Why two separate worker entry points instead of one with a flag?**
- Clearer separation of concerns
- Easier to configure different resource limits in Docker
- Simpler code (no conditional logic in main loop)
- Better observability (separate logs and metrics)

**Why aio-pika over pika?**
- Project uses asyncio throughout (FastAPI, SQLAlchemy async)
- aio-pika provides native async/await support
- Better performance in async context
- Consistent with project architecture

**Why keep database models unchanged?**
- TaskRun and DocumentIndexJob still need database persistence
- Queue only handles distribution, not storage
- Maintains audit trail and status tracking
- Allows fallback to polling if needed

### Migration Strategy

**Backward Compatibility**:
- Old worker/main.py polling loop can coexist temporarily
- Set environment variable to choose mode: `WORKER_MODE=rabbitmq` or `WORKER_MODE=polling`
- Gradual rollout: enable RabbitMQ for new tasks, polling for existing

**Rollback Plan**:
- If RabbitMQ fails, revert docker-compose.yml to single worker service
- Remove queue publish calls from backend
- Workers automatically fall back to database polling

### Rollout Guardrails (Required)

- Add `WORKER_MODE` to `worker/config.py` with default `polling`
- Keep existing `worker/main.py` polling loop intact as fallback path
- New specialized workers (`worker_taskrun.py`, `worker_indexjob.py`) are used only when `WORKER_MODE=rabbitmq`
- Compose defaults to `WORKER_MODE=rabbitmq` for new workers, and can be switched back without code rollback

### Performance Expectations

**Before (Database Polling)**:
- Task response latency: 5 seconds (polling interval)
- Database queries: N workers × 12 queries/minute = high load
- Scalability: Limited by database connection pool

**After (RabbitMQ)**:
- Task response latency: <100ms (near-instant)
- Database queries: Only on task execution (not polling)
- Scalability: Horizontal (add workers as needed)

### Operational Considerations

**Monitoring**:
- RabbitMQ management UI: http://localhost:15672
- Queue depth alerts (if queue grows, add workers)
- Consumer count monitoring
- Message rate tracking

**Resource Allocation**:
- TaskRun workers: Higher memory (512MB+), need Docker socket
- IndexJob workers: Lower memory (256MB), no Docker needed
- RabbitMQ: ~200MB memory, minimal CPU

**Troubleshooting**:
- Check RabbitMQ logs: `docker compose logs rabbitmq`
- Check worker logs: `docker compose logs worker-taskrun worker-indexjob`
- Verify queue exists: `rabbitmqadmin list queues`
- Check message count: RabbitMQ management UI
