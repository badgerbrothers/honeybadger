# Feature: Implement Sandbox Pool

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Introduce a reusable sandbox pool for `worker-taskrun` so TaskRun execution no longer creates and destroys a Docker container on every run. The pool should prewarm a bounded set of reusable sandbox containers, lease them atomically to TaskRuns, reset them safely after execution, health-check them before reuse, and refill capacity when containers are broken or drained.

The goal is to reduce cold-start latency and container churn while preserving practical task isolation through deterministic cleanup and container lifecycle controls.

## User Story

As a platform operator
I want TaskRuns to lease reusable prewarmed sandboxes from a managed pool
So that task startup is faster and worker throughput improves without giving up controlled isolation

## Problem Statement

The current worker path creates a new Docker sandbox for every TaskRun and destroys it in `finally`. This provides strong isolation, but every run pays container create/start overhead, increases Docker churn, and limits throughput under load. The existing `sandbox_sessions` model is shaped around one-off execution and does not support pool inventory, lease state, health, or capacity management.

## Solution Statement

Evolve the current sandbox runtime from a per-run ephemeral model to a pool-backed model with six core capabilities:

- precreate/prewarm sandboxes
- lease/return sandboxes
- explicit pool state management
- reset/cleanup before reuse
- health checks before return to `available`
- bounded capacity control with refill/recycle

To minimize codebase churn, implement pool state on the existing `sandbox_sessions` table instead of introducing a second pool table. Make `task_run_id` nullable so an idle pooled sandbox can exist without a bound run, then add pool-specific metadata such as `status`, `workspace_dir`, `leased_at`, `last_used_at`, `last_health_check_at`, and `reuse_count`. Keep the worker execution shape mostly intact, but replace `create -> run -> destroy` with `lease -> run -> reset/health -> return or recycle`.

## Feature Metadata

**Feature Type**: Enhancement  
**Estimated Complexity**: High  
**Primary Systems Affected**: `worker`, shared DB models, service DB init paths, Docker Compose worker config  
**Dependencies**: Docker SDK for Python, SQLAlchemy async ORM, PostgreSQL row locking, existing Docker sandbox image

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/main.py:562-728` - Current sandbox lookup, creation, TaskRun execution, and cleanup flow that must be replaced with pool lease/return logic.
- `worker/sandbox/manager.py:10-63` - Current high-level sandbox lifecycle wrapper; this is the natural place to extend manager semantics or add pool-aware helpers.
- `worker/sandbox/docker_backend.py:18-81` - Low-level Docker SDK wrapper for `containers.create`, `start`, `stop`, `remove`, and `exec_run`; reuse this rather than introducing direct Docker client calls elsewhere.
- `shared/db_models/sandbox.py:13-27` - Shared `SandboxSession` schema used by worker runtime; best candidate for pool metadata expansion.
- `worker/db_models.py:7-40` - Compatibility import layer that exposes shared DB models to worker code.
- `worker/config.py:7-73` - Existing environment-driven settings pattern; pool knobs must be added here.
- `services/task-service/app/models/sandbox.py:9-22` - Task-service local copy of `SandboxSession`; must stay schema-compatible with shared model.
- `services/project-service/app/models/sandbox.py:9-22` - Project-service local copy of `SandboxSession`; must stay schema-compatible.
- `services/rag-service/app/models/sandbox.py:9-22` - RAG-service local copy of `SandboxSession`; must stay schema-compatible.
- `services/task-service/app/database.py:31-213` - Existing `create_all + ALTER TABLE IF NOT EXISTS` compatibility migration style; follow this pattern for pool columns.
- `services/project-service/app/database.py:31-94` - Additional DB init path that must not drift from schema reality.
- `services/rag-service/app/database.py:31-151` - Additional DB init path that must not drift from schema reality.
- `worker/tests/test_sandbox_manager.py:8-82` - Unit test style for sandbox manager lifecycle and patching `DockerBackend`.
- `worker/tests/test_main.py:303-398` - Existing worker execution tests covering duplicate sandbox sessions and cleanup-on-failure patterns; mirror these when refactoring to pool semantics.
- `worker/tools/__init__.py:19-39` - Tools receive `workspace_dir` from the sandbox manager; pool reset must preserve the expected workspace contract.
- `docker-compose.yml:268-300` - Runtime environment and Docker socket mount for `worker-taskrun`; pool sizing config will plug in here.
- `CLAUDE.md:1-31` - Project baseline and runtime architecture; confirms `worker/` is the execution plane and `services/*` are the active runtime baseline.
- `docs/testing-guidelines.md:16-110` - Testing conventions, mocking guidance, and coverage expectations for backend work.

### New Files to Create

- `worker/sandbox/pool_service.py` - Pool orchestration service implementing prewarm, lease, return, reset, recycle, and refill.
- `worker/tests/test_sandbox_pool_service.py` - Unit tests for pool lifecycle, state transitions, and failure handling.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [SQLAlchemy AsyncIO Integration](https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html)
  - Specific section: async sessions and transactions
  - Why: pool lease/return logic must run safely inside async DB sessions
- [SQLAlchemy `with_for_update`](https://docs.sqlalchemy.org/20/core/selectable.html#sqlalchemy.sql.expression.GenerativeSelect.with_for_update)
  - Specific section: `skip_locked`
  - Why: atomic sandbox leasing across concurrent workers should use row locking instead of ad hoc in-memory locks
- [Docker SDK for Python: Containers](https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.create)
  - Specific section: `containers.create`
  - Why: pool prewarm and recycle still rely on correct create/start semantics and resource flags
- [Docker SDK for Python: `exec_run`](https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.Container.exec_run)
  - Specific section: command execution
  - Why: reset and health-check steps should reuse the existing command execution path instead of shelling out differently

### Patterns to Follow

**Naming Conventions:**

- Python modules use `snake_case`, classes use `CamelCase`, enum/status strings are lowercase underscore-separated.
- Existing worker configuration names use `sandbox_*` and `worker_*` prefixes in [`worker/config.py:55-62`](worker/config.py:55-62).
- Keep pool names aligned with existing runtime vocabulary: `SandboxSession`, `SandboxManager`, `DockerBackend`, `worker-taskrun`.

**Error Handling:**

- Worker code classifies failures by execution phase and emits structured failure events in [`worker/main.py:682-709`](worker/main.py:682-709).
- Sandbox-specific low-level errors are wrapped in domain exceptions inside [`worker/sandbox/docker_backend.py:43-81`](worker/sandbox/docker_backend.py:43-81).
- Follow the same pattern: wrap Docker/pool failures in worker-specific domain errors, then let `execute_task_run` classify them.

**Logging Pattern:**

- Use `structlog.get_logger()` with structured event names, as shown in [`worker/main.py:591-593`](worker/main.py:591-593) and [`worker/worker_taskrun.py:37-43`](worker/worker_taskrun.py:37-43).
- Prefer event names like `sandbox_leased`, `sandbox_returned`, `sandbox_reset_failed`, `sandbox_recycled`, `sandbox_pool_refilled`.

**Database / Compatibility Pattern:**

- The repository does not use Alembic for these Python services; schema evolution is done via `Base.metadata.create_all` plus explicit `ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS` in service startup init code.
- Any schema expansion for `sandbox_sessions` must be mirrored in all three service model copies and at least task-service DB init. For safety and startup consistency, update all three DB init files.

**Testing Pattern:**

- Worker tests use `pytest.mark.asyncio`, `AsyncMock`, and module patching via `patch.dict(sys.modules, ...)`, as shown in [`worker/tests/test_main.py:329-394`](worker/tests/test_main.py:329-394).
- New pool tests should stay unit-level and mock Docker plus DB session behavior rather than requiring a live Docker daemon.

**Anti-Patterns to Avoid:**

- Do not store pool state only in process memory; multiple workers and restarts would make leases unsafe.
- Do not lease sandboxes without DB row locking; duplicate lease bugs are likely under parallel consumers.
- Do not reset sandboxes only by clearing files; lingering processes or failed health checks must force recycle.
- Do not introduce a second direct Docker client outside `DockerBackend`.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Extend the existing sandbox data model and configuration so the worker can reason about pool inventory instead of one-shot sessions.

**Tasks:**

- Expand `SandboxSession` schema to represent pooled inventory
- Add pool configuration settings
- Add compatibility DDL for new columns and nullable lease ownership
- Define pool status vocabulary and lifecycle rules

### Phase 2: Core Implementation

Build a dedicated pool orchestration layer that prewarms sandboxes, leases one atomically, resets it after use, and recycles broken entries.

**Tasks:**

- Implement pool service with `ensure_min_capacity`
- Implement atomic `lease_sandbox`
- Implement `return_sandbox`
- Implement `reset_sandbox`
- Implement `health_check_sandbox`
- Implement `recycle_sandbox` and refill logic

### Phase 3: Integration

Refactor worker execution to use the pool service instead of direct per-run create/destroy, while preserving existing task events and tool workspace behavior.

**Tasks:**

- Replace sandbox creation path in `execute_task_run`
- Preserve `workspace_dir` injection into tools
- Record lease metadata and state transitions
- Refill pool at worker startup and after recycle events
- Add Compose env wiring for pool knobs

### Phase 4: Testing & Validation

Add focused unit tests for pool state transitions and refactor existing worker execution tests to assert lease/return behavior rather than create/destroy behavior only.

**Tasks:**

- Add pool service unit tests
- Update worker execution tests
- Add schema compatibility tests where feasible
- Validate lint, targeted unit tests, and manual runtime behavior

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Guidelines

Use information-dense keywords for clarity:

- **CREATE**: New files or components
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **REMOVE**: Delete deprecated code
- **REFACTOR**: Restructure without changing behavior
- **MIRROR**: Copy pattern from elsewhere in codebase

### UPDATE `shared/db_models/sandbox.py`

- **IMPLEMENT**: Evolve `SandboxSession` from per-run-only record into reusable pool row by making `task_run_id` nullable and adding `status`, `workspace_dir`, `leased_at`, `last_used_at`, `last_health_check_at`, `reuse_count`, and optional `lease_error` or `drain_reason`.
- **PATTERN**: Mirror existing SQLAlchemy mapped-column style from `shared/db_models/sandbox.py:13-27`.
- **IMPORTS**: `String`, `Integer`, `DateTime` or equivalent SQLAlchemy types, optional Python enum if represented as string-backed values.
- **GOTCHA**: Keep `container_id` indexed and unique enough for reuse semantics; avoid PostgreSQL enum migration complexity unless absolutely needed.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run python -c "from shared.db_models.sandbox import SandboxSession; print(SandboxSession.__tablename__)"`

### MIRROR `services/*/app/models/sandbox.py`

- **IMPLEMENT**: Apply the same schema fields and nullability to:
  - `services/task-service/app/models/sandbox.py`
  - `services/project-service/app/models/sandbox.py`
  - `services/rag-service/app/models/sandbox.py`
- **PATTERN**: Mirror the local model copy pattern already used across services.
- **IMPORTS**: Keep imports aligned with each service model base.
- **GOTCHA**: Drift between shared and service copies will cause `create_all` and runtime assumptions to diverge.
- **VALIDATE**: `cd /d F:\Programs\project_4 && rg -n "workspace_dir|reuse_count|last_health_check_at|task_run_id" shared/db_models/sandbox.py services/*/app/models/sandbox.py`

### UPDATE `services/task-service/app/database.py`

- **IMPLEMENT**: Add compatibility DDL to backfill new pool columns and relax `task_run_id` to nullable. If necessary, also add indexes for `status` and `last_used_at`.
- **PATTERN**: Follow explicit `ALTER TABLE IF EXISTS ... ADD COLUMN IF NOT EXISTS` style from `services/task-service/app/database.py:46-207`.
- **IMPORTS**: Reuse existing `text` helper and transaction pattern.
- **GOTCHA**: PostgreSQL needs explicit `ALTER COLUMN ... DROP NOT NULL`; do not assume `create_all` will mutate an existing column definition.
- **VALIDATE**: `cd /d F:\Programs\project_4\services\task-service && uv run python -c "import app.database; print('task-service db init import ok')"`

### UPDATE `services/project-service/app/database.py` AND `services/rag-service/app/database.py`

- **IMPLEMENT**: Mirror the compatibility DDL needed for pool columns and nullable `task_run_id` so any service startup path can converge schema state.
- **PATTERN**: Match their existing `init_db()` structure and advisory lock usage.
- **IMPORTS**: No new library dependencies.
- **GOTCHA**: These services do not use the pool directly, but they still run `Base.metadata.create_all`; stale local models can silently fight the schema.
- **VALIDATE**: `cd /d F:\Programs\project_4 && uv run python -c "print('manual validation: inspect database init files updated')"`

### UPDATE `worker/config.py`

- **IMPLEMENT**: Add pool knobs such as `sandbox_pool_enabled`, `sandbox_pool_min_size`, `sandbox_pool_max_size`, `sandbox_max_reuse_count`, `sandbox_lease_timeout_seconds`, and `sandbox_healthcheck_command`.
- **PATTERN**: Follow current Pydantic settings field style in `worker/config.py:55-62`.
- **IMPORTS**: `Field` only if alias/default behavior is needed.
- **GOTCHA**: Keep sane defaults that preserve current behavior when pooling is disabled or min size is zero.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run python -c "from config import settings; print(settings.sandbox_image)"`

### CREATE `worker/sandbox/pool_service.py`

- **IMPLEMENT**: Build the pool orchestration service with methods for:
  - `ensure_min_capacity(session)`
  - `create_pooled_sandbox(session)`
  - `lease_sandbox(session, task_run_id)`
  - `return_sandbox(session, sandbox_session, healthy=True)`
  - `reset_sandbox(sandbox_manager)`
  - `health_check_sandbox(sandbox_manager)`
  - `recycle_sandbox(session, sandbox_session, reason)`
- **PATTERN**: Reuse `SandboxManager` and `DockerBackend` as the only Docker abstraction layer, mirroring `worker/sandbox/manager.py:29-53`.
- **IMPORTS**: `select`, `func` if needed, `structlog`, `SandboxSession`, `SandboxManager`, worker settings.
- **GOTCHA**: Leasing must use `SELECT ... FOR UPDATE SKIP LOCKED` or equivalent SQLAlchemy async pattern to remain safe with concurrent workers.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run python -c "from sandbox.pool_service import SandboxPoolService; print(SandboxPoolService.__name__)"`

### REFACTOR `worker/sandbox/manager.py`

- **IMPLEMENT**: Support rebuilding a `SandboxManager` from a leased DB row, preserve `workspace_dir` for pooled containers, and expose helpers needed by pool reset/health logic without forcing destroy-on-context-exit semantics.
- **PATTERN**: Keep manager as the high-level lifecycle wrapper, not a second pool implementation.
- **IMPORTS**: Existing `DockerBackend`, `Path`, `tempfile`, `shutil`, plus any new classmethods/helpers.
- **GOTCHA**: Do not break current `PythonTool` contract that expects a manager with `workspace_dir` and `execute()`.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run pytest tests/test_sandbox_manager.py -v`

### UPDATE `worker/main.py`

- **IMPLEMENT**: Replace the current `sandbox_lookup -> SandboxManager(...) -> create() -> destroy()` path with:
  - pool capacity ensure on demand
  - atomic lease for current `task_run_id`
  - bind leased sandbox to tools
  - on success: reset + health check + return
  - on failure: attempt reset; recycle if reset/health fails
- **PATTERN**: Preserve existing run event emission and error classification structure from `worker/main.py:560-729`.
- **IMPORTS**: `SandboxPoolService`, updated sandbox status helpers, possibly new exception types.
- **GOTCHA**: Keep existing behavior where duplicate execution for the same running task does not lease a second sandbox; the duplicate check moves from “existing session row” to “already leased session for this task run”.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run pytest tests/test_main.py -v`

### UPDATE `worker/worker_taskrun.py`

- **IMPLEMENT**: Prewarm or reconcile pool state during worker startup before consuming queue messages.
- **PATTERN**: Match current startup sequence around `client.connect()` in `worker/worker_taskrun.py:46-71`.
- **IMPORTS**: `async_session_maker`, `SandboxPoolService`.
- **GOTCHA**: Startup prewarm should not block forever if Docker is temporarily unhealthy; log and continue with degraded behavior if configured.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run python -m worker.worker_taskrun`

### UPDATE `docker-compose.yml`

- **IMPLEMENT**: Add pool environment variables for `worker-taskrun`, with defaults that preserve a small initial pool.
- **PATTERN**: Follow existing worker env block in `docker-compose.yml:274-297`.
- **IMPORTS**: None.
- **GOTCHA**: Do not add pool settings to `worker-indexjob`; index workers do not use sandbox execution.
- **VALIDATE**: `cd /d F:\Programs\project_4 && docker compose config`

### CREATE `worker/tests/test_sandbox_pool_service.py`

- **IMPLEMENT**: Add unit tests covering:
  - prewarm up to min size
  - lease chooses `available` row
  - concurrent-safe lease intent via locked query abstraction
  - return sets `available` and clears `task_run_id`
  - reset failure causes recycle
  - health failure causes recycle
  - max reuse count causes drain/recreate
- **PATTERN**: Mirror mocking style from `worker/tests/test_sandbox_manager.py:8-82` and `worker/tests/test_main.py:329-394`.
- **IMPORTS**: `pytest`, `AsyncMock`, `Mock`, `patch`, `uuid`.
- **GOTCHA**: Keep tests unit-level; do not require live Docker or PostgreSQL.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run pytest tests/test_sandbox_pool_service.py -v`

### UPDATE `worker/tests/test_main.py`

- **IMPLEMENT**: Replace assumptions about direct `SandboxManager.create()` and `.destroy()` with pool lease/return assertions. Add regression tests for:
  - duplicate task run does not lease a second sandbox
  - failed return triggers recycle
  - successful run returns sandbox to `available`
- **PATTERN**: Preserve current execution-path testing style and use `patch.dict(sys.modules, ...)` only where still necessary.
- **IMPORTS**: `SandboxPoolService` fakes/mocks, `AsyncMock`, `Mock`.
- **GOTCHA**: Existing tests that assert sandbox session insert behavior will need to be rewritten to assert pool state transitions instead.
- **VALIDATE**: `cd /d F:\Programs\project_4\worker && uv run pytest tests/test_main.py tests/test_sandbox_manager.py tests/test_sandbox_pool_service.py -v`

---

## TESTING STRATEGY

The project already treats worker tests as unit-heavy `pytest` suites with mocked external systems. Follow that pattern and keep the first implementation pass fully testable without Docker or PostgreSQL.

### Unit Tests

- `worker/tests/test_sandbox_pool_service.py`
  - prewarm logic creates only up to configured min size
  - lease marks row `leased`, binds `task_run_id`, increments `reuse_count` when appropriate
  - return clears lease metadata and sets `available`
  - broken/draining sandboxes are never leased
  - health/reset failures trigger recycle and refill
- `worker/tests/test_sandbox_manager.py`
  - preserve current lifecycle tests
  - add any helper-specific tests needed for pooled manager reconstruction
- `worker/tests/test_main.py`
  - worker execution path uses pool instead of direct create/destroy
  - failure path still cleans up correctly
  - duplicate execution remains single-lease

Design unit tests with fixtures and assertions following existing mocking approaches in `worker/tests/test_main.py` and `worker/tests/test_sandbox_manager.py`.

### Integration Tests

- Manual compose-backed verification only for first pass:
  - start stack with `worker-taskrun`
  - verify pool prewarms configured count
  - run two TaskRuns sequentially and confirm same container can be reused after reset
  - run a fault-injected task and verify broken sandbox is recycled and pool is refilled

### Edge Cases

- no available sandbox and pool already at max size
- two workers race to lease the same sandbox
- worker crashes after lease but before return
- reset command partially succeeds but health check fails
- stale leased sandbox exceeds lease timeout
- Docker remove fails during recycle
- multiple null `task_run_id` rows coexist correctly after nullability change
- pool disabled should preserve current behavior or cleanly bypass pool path

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd /d F:\Programs\project_4\worker
uv run ruff check .
```

### Level 2: Unit Tests

```bash
cd /d F:\Programs\project_4\worker
uv run pytest tests/test_sandbox_manager.py tests/test_sandbox_pool_service.py tests/test_main.py -v
```

### Level 3: Integration Tests

```bash
cd /d F:\Programs\project_4
docker compose up -d postgres redis minio rabbitmq task-service worker-taskrun
```

Then submit at least one TaskRun through the existing backend flow and inspect worker logs:

```bash
docker compose logs worker-taskrun --tail=200
```

### Level 4: Manual Validation

1. Set pool env vars in `docker-compose.yml` or `.env` with a small min size such as `2`.
2. Start `worker-taskrun` and confirm logs show prewarm events and `available` pool entries.
3. Run one TaskRun and verify logs show `sandbox_leased`, `sandbox_returned`, and no new container creation beyond pool warmup.
4. Run a second TaskRun and verify the sandbox is reused after reset.
5. Force a reset or health failure and verify logs show `sandbox_recycled` followed by refill to min capacity.

### Level 5: Additional Validation (Optional)

```bash
cd /d F:\Programs\project_4
docker compose config
```

Inspect `sandbox_sessions` rows directly in PostgreSQL if needed to verify status transitions.

---

## ACCEPTANCE CRITERIA

- [ ] `worker-taskrun` supports prewarming a configurable minimum number of sandbox containers
- [ ] TaskRuns lease pooled sandboxes atomically instead of always creating a new container
- [ ] Returned sandboxes are reset and health-checked before becoming reusable
- [ ] Broken or unhealthy sandboxes are recycled and pool capacity is refilled
- [ ] Pool size respects configured min/max bounds
- [ ] Existing tool workspace contract continues to work with leased sandboxes
- [ ] Worker unit tests cover pool lifecycle and refactored execution flow
- [ ] Service-side DB init remains compatible with expanded `sandbox_sessions` schema
- [ ] `worker-indexjob` behavior is unchanged
- [ ] All validation commands pass with zero errors

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

- Preferred first-pass design: reuse `sandbox_sessions` as the pool inventory table. This avoids introducing a brand new cross-service table and keeps schema changes localized to an already-shared concept.
- Store status as a string column first. A PostgreSQL enum would add migration complexity with little benefit at this stage.
- Use `task_run_id` as the current lease owner and clear it on return. This sacrifices persistent history, but matches the repository's current operational style and minimizes schema surface area.
- If post-implementation analysis shows the loss of historical lease records is a problem, add a dedicated audit table in a second phase rather than mixing that concern into the first delivery.
- Design reset to be conservative:
  - clear workspace contents
  - remove obvious temp files
  - kill leftover processes if possible
  - run a health-check command
  - recycle on any uncertain state
- Confidence Score: 8/10 that execution will succeed on first attempt
