# Feature: Refactor RAG Service Internal Architecture

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Refactor `services/rag-service` so that indexing orchestration and search logic are separated into distinct internal modules without changing the current microservice boundary. The result should keep `rag-service` as the control plane for RAG APIs and job scheduling, keep `worker` as the execution plane for indexing, and reduce confusion caused by the current all-in-one `rag_service.py`.

This is an internal architecture refactor. It should preserve existing HTTP APIs and queue behavior while making the codebase easier to extend and safer to change. It should also prepare a later step where duplicated RAG core logic can be consolidated across `rag-service` and `worker`.

## User Story

As a backend engineer
I want `rag-service` search and indexing orchestration responsibilities separated
So that I can safely evolve RAG behavior without mixing unrelated concerns or breaking queue-driven indexing

## Problem Statement

`services/rag-service/app/services/rag_service.py` currently mixes:

- index job creation and RabbitMQ publishing
- chunk search and vector search
- query rewrite and reranking setup
- chunk listing and deletion
- project node requeue orchestration

This creates several issues:

- search-related objects are eagerly initialized even when only index scheduling is needed
- router dependencies hide two distinct responsibilities behind one singleton
- future changes to retrieval logic risk accidental impact on indexing flow
- the service boundary between `rag-service` and `worker` is harder to reason about
- duplicated RAG core logic across `services/rag-service/app/rag` and `worker/rag` remains harder to unwind

## Solution Statement

Split the current `RagService` into two internal service-layer modules inside `services/rag-service`:

- `index_job_service.py`: queue-facing orchestration for `DocumentIndexJob` creation and `ProjectNode` requeue
- `search_service.py`: search-facing orchestration for hybrid retrieval, query rewrite, reranking, vector search, chunk listing, and chunk deletion

Keep routers thin and explicit:

- `app/routers/rag.py` depends on `search_service` and `index_job_service`
- `app/routers/rag_collections.py` depends on `index_job_service` for upload-triggered scheduling

Do not introduce a new microservice in this feature. Do not move indexing execution out of `worker`. Do not change external API routes unless required for bug fixes. Treat shared RAG core extraction as a documented follow-on, not the primary implementation scope.

## Feature Metadata

**Feature Type**: Refactor
**Estimated Complexity**: Medium
**Primary Systems Affected**: `services/rag-service`, `worker`, RabbitMQ integration tests
**Dependencies**: FastAPI, SQLAlchemy async, aio-pika/RabbitMQ, pgvector, OpenAI SDK, existing worker RAG implementation

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `services/rag-service/app/services/rag_service.py` (lines 23-223) - Mixed orchestration/search singleton that must be split.
- `services/rag-service/app/routers/rag.py` (lines 13-117) - Current project-RAG API surface; shows existing router/dependency pattern.
- `services/rag-service/app/routers/rag_collections.py` (lines 137-214) - Upload flow that schedules indexing after storage upload succeeds.
- `services/rag-service/app/services/queue_service.py` (lines 17-62) - Canonical queue publishing pattern and failure behavior.
- `services/rag-service/app/main.py` (lines 9-44) - Router registration and startup/shutdown queue lifecycle.
- `services/rag-service/app/rag/hybrid_retriever.py` (entire file) - Current retrieval implementation to preserve for now.
- `services/rag-service/app/rag/embeddings.py` (entire file) - Embedding creation and local fallback behavior.
- `worker/main.py` (lines 181-229) - Runtime task-context retrieval currently performed in worker.
- `worker/main.py` (lines 279-326) - Index job execution path showing worker ownership of parsing/chunking/embedding/storage writes.
- `worker/rag/indexer.py` (lines 16-159) - Current indexing execution baseline in worker.
- `worker/rag/retriever.py` (lines 12-102) - Worker retrieval baseline and scope-handling behavior.
- `services/rag-service/tests/test_rag_collections_api.py` (lines 21-78) - Router test pattern using `FastAPI`, dependency overrides, and `AsyncMock`.
- `services/rag-service/tests/test_hybrid_retriever.py` (entire file) - Pure unit test pattern for retrieval helpers.
- `services/rag-service/tests/test_query_rewriter.py` (entire file) - Pure unit test pattern for search helper classes.
- `worker/tests/test_indexer.py` (entire file) - Existing worker indexing test style to preserve expected behavior.
- `worker/tests/test_retriever.py` (entire file) - Existing worker retrieval scope tests to mirror in service-side search tests.
- `docs/current-system-architecture.md` - Current runtime architecture baseline; verify against code before implementing.
- `docs/rag-refactor-plan.md` - Prior internal RAG refactor notes; useful as historical context only because parts of it refer to older layout.

### New Files to Create

- `services/rag-service/app/services/index_job_service.py` - Index scheduling and project-node requeue orchestration.
- `services/rag-service/app/services/search_service.py` - Search orchestration and chunk management.
- `services/rag-service/tests/test_index_job_service.py` - Unit tests for job creation, publish failure rollback semantics, and node requeue cases.
- `services/rag-service/tests/test_search_service.py` - Unit tests for search branching, thresholding, query rewrite toggles, and vector-search fallback.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
  - Specific section: APIRouter organization and dependency separation
  - Why: Confirms the current router-thin/service-layer approach is aligned with official FastAPI structuring guidance.
- [SQLAlchemy AsyncIO ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - Specific section: `async_sessionmaker`, session scoping, and async ORM usage
  - Why: Needed to preserve correct async transaction handling when splitting service methods.
- [RabbitMQ Work Queues Tutorial](https://www.rabbitmq.com/tutorials/tutorial-two-python)
  - Specific section: durable queues and persistent messages
  - Why: Confirms existing queue durability semantics should remain unchanged during refactor.
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
  - Specific section: app composition and test client patterns
  - Why: Matches the router-level testing pattern already used in `services/rag-service/tests`.

### Patterns to Follow

**Naming Conventions**

- Modules are `snake_case`.
- Router files align to domain nouns: `rag.py`, `rag_collections.py`.
- Service singletons are module-level instances: `queue_service = QueueService()`, `rag_service = RagService()`.
- Prefer descriptive methods: `schedule_indexing`, `requeue_node`, `search`, `list_chunks`, `delete_chunk`.

**Error Handling**

- Router ownership checks use small `_get_owned_*_or_404` helpers and raise `HTTPException`.
- Services log and re-raise infrastructure failures after updating persisted state.
- Queue publish failure currently marks `DocumentIndexJob.status = FAILED` and writes `error_message = "queue_publish_failed"` before re-raising. Preserve this behavior.

**Logging Pattern**

- Use `structlog.get_logger(__name__)`.
- Log infrastructure failures with structured fields and `exc_info=True`.
- Queue publisher logs success and failure at service boundaries, not inside routers.

**Other Relevant Patterns**

- Routers should stay thin and delegate domain work to services.
- `services/rag-service/tests/test_rag_collections_api.py` overrides FastAPI dependencies and patches module-level service objects directly.
- Worker owns indexing execution. `rag-service` should not parse files or generate embeddings as part of job scheduling.
- Current anti-pattern to remove: eager search-object initialization inside index-scheduling singleton.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Clarify internal `rag-service` boundaries without changing external behavior.

**Tasks:**

- Define explicit split between index orchestration and search orchestration.
- Introduce new service modules with narrow responsibilities.
- Keep current route paths, request/response shapes, and queue names unchanged.

### Phase 2: Core Implementation

Move logic out of `rag_service.py` into the new modules.

**Tasks:**

- Implement index job service for `schedule_indexing` and `requeue_node`.
- Implement search service for search/list/delete operations and search helper initialization.
- Remove mixed responsibilities from the old service entrypoint or replace it with a minimal compatibility facade.

### Phase 3: Integration

Reconnect routers and tests to the new services.

**Tasks:**

- Update `rag.py` to import the new services explicitly.
- Update `rag_collections.py` to use the index job service after upload succeeds.
- Ensure `main.py` router registration remains unchanged.
- Keep worker contracts and queue payload shape unchanged.

### Phase 4: Testing & Validation

Prove the refactor did not change behavior.

**Tasks:**

- Add unit tests for both new service modules.
- Keep existing router tests green.
- Run existing retrieval/indexer-related tests to confirm worker integration remains intact.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### REFACTOR services/rag-service/app/services/index_job_service.py

- **IMPLEMENT**: Create `IndexJobService` with `schedule_indexing(...)` and `requeue_node(...)`, moving logic from `rag_service.py:35-77` and `rag_service.py:197-215`.
- **PATTERN**: Mirror queue failure logging and state mutation from `services/rag-service/app/services/rag_service.py:60-76`.
- **IMPORTS**: `uuid`, `structlog`, `AsyncSession`, `select`, `DocumentIndexJob`, `DocumentIndexStatus`, `ProjectNode`, `queue_service`.
- **GOTCHA**: Preserve queue payload shape and failure semantics exactly; implementation must not accidentally import or initialize search helpers.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_index_job_service.py -q`

### REFACTOR services/rag-service/app/services/search_service.py

- **IMPLEMENT**: Create `SearchService` with `search(...)`, `_vector_search(...)`, `list_chunks(...)`, and `delete_chunk(...)`, moving logic from `rag_service.py:79-195`.
- **PATTERN**: Mirror hybrid-search branch from `services/rag-service/app/services/rag_service.py:97-120`.
- **IMPORTS**: `uuid`, `structlog`, `AsyncSession`, `select`, `delete`, `DocumentChunk`, `EmbeddingService`, `HybridRetriever`, `QueryRewriter`, `RerankerService`, `settings`.
- **GOTCHA**: Lazy-initialize search helpers inside `SearchService` rather than module import time if feasible; if keeping a singleton, ensure only search-specific objects live there.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_search_service.py -q`

### UPDATE services/rag-service/app/routers/rag.py

- **IMPLEMENT**: Replace `from app.services.rag_service import rag_service` with explicit imports from `index_job_service` and `search_service`.
- **PATTERN**: Keep ownership checks and response structure identical to `services/rag-service/app/routers/rag.py:26-117`.
- **IMPORTS**: `index_job_service`, `search_service`.
- **GOTCHA**: `/{project_id}/documents/index` must still return `job_id`, `status`, `project_id`, `node_id`; `/{project_id}/search` option flags must remain backward compatible.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py -q`

### UPDATE services/rag-service/app/routers/rag_collections.py

- **IMPLEMENT**: Replace scheduling dependency on old `rag_service` singleton with `index_job_service`.
- **PATTERN**: Preserve upload sequencing from `services/rag-service/app/routers/rag_collections.py:175-214` - upload to storage first, persist metadata, then schedule indexing.
- **IMPORTS**: `index_job_service`.
- **GOTCHA**: Failure path currently tries to mark `RagCollectionFile` failed after rollback; do not weaken that behavior.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py -q`

### UPDATE services/rag-service/app/services/rag_service.py

- **IMPLEMENT**: Convert to a minimal compatibility facade or remove direct router imports from it, depending on how broadly it is referenced. Preferred outcome: keep only a small transitional wrapper or delete and update all imports.
- **PATTERN**: Use explicit imports from the new modules rather than duplicating logic.
- **IMPORTS**: New service modules only if keeping facade.
- **GOTCHA**: Do not leave dead duplicate implementations behind; that defeats the refactor.
- **VALIDATE**: `rg -n "from app\\.services\\.rag_service import rag_service|rag_service\\." services/rag-service`

### CREATE services/rag-service/tests/test_index_job_service.py

- **IMPLEMENT**: Add service-level tests for successful job creation, queue publish failure, and `requeue_node(...)` missing-node handling.
- **PATTERN**: Mirror `AsyncMock` style and lightweight DB setup from `services/rag-service/tests/test_rag_collections_api.py:21-78`.
- **IMPORTS**: `pytest`, `AsyncMock`, async SQLAlchemy test engine/session setup, service module, models.
- **GOTCHA**: Patch `queue_service.publish_index_job` rather than opening a real RabbitMQ connection.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_index_job_service.py -q`

### CREATE services/rag-service/tests/test_search_service.py

- **IMPLEMENT**: Add tests for hybrid path, vector-only path, query rewrite toggle, reranker toggle, threshold filtering, list chunks, and delete chunk.
- **PATTERN**: Mirror helper testing style from `services/rag-service/tests/test_hybrid_retriever.py` and `services/rag-service/tests/test_query_rewriter.py`.
- **IMPORTS**: `pytest`, `AsyncMock`, service module, lightweight chunk fixtures or mocked DB execution results.
- **GOTCHA**: Make one test assert that search-specific helpers are not initialized by index-service imports.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_search_service.py -q`

### UPDATE services/rag-service/app/main.py

- **IMPLEMENT**: Only if import paths change or facade removal requires startup imports to be adjusted. Keep router registration and queue lifecycle unchanged.
- **PATTERN**: Preserve startup/shutdown behavior from `services/rag-service/app/main.py:12-24`.
- **IMPORTS**: New service modules only if needed.
- **GOTCHA**: Do not introduce new startup dependencies that can fail because OpenAI credentials are absent when only index scheduling is used.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests -q`

### ADD architecture note in docs or plan-adjacent doc

- **IMPLEMENT**: Document that this refactor is internal-only and that shared RAG core extraction remains a follow-on step.
- **PATTERN**: Mirror concise architecture notes used in `README.md` and `docs/current-system-architecture.md`.
- **IMPORTS**: None.
- **GOTCHA**: Do not claim that duplication with `worker/rag` has been fully eliminated if this feature only cleans up `rag-service`.
- **VALIDATE**: `rg -n "SearchService|IndexJobService|shared RAG core" docs services/rag-service`

---

## TESTING STRATEGY

The project uses `pytest` and `pytest-asyncio` for Python services. Service tests should stay lightweight and mostly avoid real external dependencies. Router tests should keep using `FastAPI`, dependency overrides, and `httpx.AsyncClient` with `ASGITransport`.

### Unit Tests

- `test_index_job_service.py`
  - successful `schedule_indexing`
  - queue publish failure updates status to `FAILED`
  - `requeue_node` returns `None` when `ProjectNode` is missing
  - `requeue_node` copies `storage_path` and `file_name` from `ProjectNode`
- `test_search_service.py`
  - hybrid path uses `HybridRetriever`
  - vector-only path bypasses `HybridRetriever`
  - query rewrite toggle uses `QueryRewriter`
  - reranker toggle applies truncation correctly
  - threshold filtering is preserved
  - `list_chunks` ordering remains stable
  - `delete_chunk` returns `False` when chunk is missing

### Integration Tests

- Keep `services/rag-service/tests/test_rag_collections_api.py` green to validate upload -> schedule flow.
- Run `services/rag-service/tests/test_hybrid_retriever.py` and `services/rag-service/tests/test_query_rewriter.py` to confirm helper behavior remains stable.
- Run worker retrieval/indexing tests to ensure this refactor did not accidentally change expected contracts:
  - `worker/tests/test_indexer.py`
  - `worker/tests/test_retriever.py`

### Edge Cases

- queue unavailable after `DocumentIndexJob` has been inserted
- upload succeeds but scheduling fails
- search called with `use_query_rewrite=false` and no OpenAI key present
- vector-only search on empty chunk set
- delete chunk with wrong `project_id`
- import-time behavior when OpenAI key is absent but only index scheduling path is exercised

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and feature correctness.

### Level 1: Syntax & Style

- `uv run --project services/rag-service python -m compileall services/rag-service/app`
- `uv run --project services/rag-service ruff check services/rag-service/app services/rag-service/tests`

### Level 2: Unit Tests

- `uv run --project services/rag-service pytest services/rag-service/tests/test_index_job_service.py -q`
- `uv run --project services/rag-service pytest services/rag-service/tests/test_search_service.py -q`
- `uv run --project services/rag-service pytest services/rag-service/tests/test_hybrid_retriever.py services/rag-service/tests/test_query_rewriter.py -q`

### Level 3: Integration Tests

- `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py -q`
- `uv run --project worker pytest worker/tests/test_indexer.py worker/tests/test_retriever.py -q`

### Level 4: Manual Validation

1. Start stack or at least `postgres`, `minio`, `rabbitmq`, `rag-service`, `worker-indexjob`.
2. Create a RAG collection through `POST /api/rags/`.
3. Upload a supported file through `POST /api/rags/{rag_id}/files/upload`.
4. Confirm a `DocumentIndexJob` row is created and published to `index-jobs`.
5. Confirm `worker-indexjob` processes the job and writes `document_chunk` rows.
6. Call `POST /api/rag/projects/{project_id}/search` or equivalent scoped search if available in your test fixture and confirm response shape is unchanged.

### Level 5: Additional Validation (Optional)

- `rg -n "from app\\.services\\.rag_service import rag_service|class RagService|rag_service = RagService\\(" services/rag-service`
- `rg -n "SearchService|IndexJobService" services/rag-service`

---

## ACCEPTANCE CRITERIA

- [ ] `rag-service` remains a single microservice; no new deployable service is introduced.
- [ ] Index job scheduling and search logic live in separate internal modules.
- [ ] Existing RAG API paths and response shapes remain backward compatible.
- [ ] Queue publish behavior and failure semantics remain unchanged.
- [ ] `worker-indexjob` continues to own parsing, chunking, embedding, and chunk persistence.
- [ ] Search-specific helper initialization is no longer tied to index job scheduling path.
- [ ] New service-level tests cover both internal modules.
- [ ] Existing router and helper tests pass without regressions.
- [ ] Documentation accurately states that shared RAG core extraction is still a follow-on step.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full relevant test suite passes
- [ ] No linting or syntax errors remain
- [ ] Manual validation confirms upload -> schedule -> index flow still works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for maintainability and future shared-core extraction

---

## NOTES

- This feature is intentionally scoped to `rag-service` internal architecture. It does not fully solve duplication between `services/rag-service/app/rag` and `worker/rag`.
- A later follow-on should decide whether shared RAG core should live under a real installable shared package or whether worker remains the single source of truth.
- If implementation cost rises, preserve the refactor by adding a temporary compatibility facade instead of partially moving logic and leaving two active implementations.
- Confidence Score: 8/10 that execution will succeed on first attempt.
