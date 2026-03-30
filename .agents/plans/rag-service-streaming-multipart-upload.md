# Feature: RAG Service Streaming Multipart Upload

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Refactor `services/rag-service` file upload paths so large document uploads no longer require reading the entire file into memory before sending it to MinIO. The target behavior is a memory-safe streaming upload path for both global RAG collection files and project files, while preserving the existing asynchronous indexing contract:

- upload file to object storage
- persist file metadata
- enqueue `DocumentIndexJob`
- let `worker-indexjob` download and index from MinIO

This feature is about upload-path architecture and performance safety, not about changing the indexing worker contract.

## User Story

As a user uploading large documents
I want the system to stream uploads into object storage instead of buffering the entire file in memory
So that large RAG and project documents upload reliably without exhausting service memory

## Problem Statement

`rag-service` currently reads the full uploaded file into memory with `await file.read()` before:

- validating size
- creating metadata records
- calling the MinIO SDK

This creates several problems:

- memory usage scales with file size
- concurrent uploads can multiply memory pressure
- the same anti-pattern is duplicated in both RAG collection and project upload endpoints
- MinIO SDK calls are currently wrapped in `async def` methods but remain blocking
- the current implementation makes raising the file-size ceiling risky

## Solution Statement

Replace the current whole-file buffering flow with a streaming upload design:

- keep FastAPI routers responsible for auth, ownership checks, extension checks, metadata creation, and job scheduling
- extend `StorageService` with a stream-oriented upload method that accepts an upload stream and content length
- feed `UploadFile.file` directly to MinIO instead of converting to `bytes`
- run blocking MinIO SDK upload work in a thread via `asyncio.to_thread(...)`
- use MinIO/S3 multipart upload behavior for large objects through `put_object(...)` with explicit multipart-related arguments
- preserve the existing post-upload behavior: metadata commit, then `index_job_service.schedule_indexing(...)`

The first implementation should optimize the server-side upload path without introducing resumable client-side uploads or changing the worker download/index flow.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: `services/rag-service` routers and storage helper, MinIO object storage integration, RAG/project upload tests
**Dependencies**: FastAPI `UploadFile`, MinIO Python SDK, Python `asyncio.to_thread`, existing RabbitMQ-backed indexing flow

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `services/rag-service/app/routers/rag_collections.py` (lines 137-214) - Current global RAG file upload flow; reads full file into memory, creates `RagCollectionFile`, uploads to storage, then schedules indexing.
- `services/rag-service/app/routers/projects.py` (lines 65-134) - Same anti-pattern for project file uploads; must stay behaviorally aligned with `rag_collections.py`.
- `services/rag-service/app/services/storage.py` (lines 14-112) - Current MinIO helper; `upload_file(...)` and `download_file(...)` are async facades over blocking SDK calls.
- `services/rag-service/app/config.py` (lines 27-53) - Existing settings pattern for RAG/object storage configuration; use this if new upload settings are needed.
- `services/rag-service/app/models/rag_collection_file.py` (lines 22-44) - Current persisted metadata for uploaded RAG files; `file_size`, `status`, and `error_message` semantics must remain coherent.
- `services/rag-service/app/schemas/rag_file.py` (entire file) - Response shape for upload/list APIs; upload refactor must not break this contract.
- `services/rag-service/app/services/index_job_service.py` (entire file) - Canonical job creation and queue publish behavior; scheduling still happens only after storage upload succeeds.
- `worker/main.py` (lines 428-496) - Index worker contract: worker downloads from `job.storage_path`, writes temp local file, indexes, and updates `DocumentIndexJob`.
- `worker/services/storage_client.py` (entire file) - Confirms worker still expects original file object to exist in MinIO and should remain unchanged for this feature.
- `services/rag-service/tests/test_rag_collections_api.py` (lines 21-78) - Existing router test pattern using dependency overrides and `AsyncMock`.
- `services/rag-service/tests/test_index_job_service.py` (lines 43-139) - Service test style and queue publish mocking pattern.
- `services/storage-service/app/main.py` (lines 70-91) - Separate service still has the same full-buffer upload anti-pattern; useful as a comparison and follow-on cleanup candidate, but not primary scope.

### New Files to Create

- `services/rag-service/tests/test_projects_api.py` - Router tests for project-file upload behavior and failure handling.
- `services/rag-service/tests/test_storage_service.py` - Unit tests for new streaming upload helper behavior, including thread-offloaded blocking upload calls and size/rewind behavior.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/)
  - Specific section: `UploadFile` vs raw `bytes`
  - Why: Confirms the server should prefer `UploadFile` for large files and avoid eager in-memory buffering.
- [FastAPI UploadFile Reference](https://fastapi.tiangolo.com/reference/uploadfile/)
  - Specific section: `.file`, `.read()`, `.seek()`, and spooled file semantics
  - Why: Needed to safely pass the underlying file object to the storage layer and rewind after any size inspection.
- [Python asyncio `to_thread`](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
  - Specific section: running blocking IO in a separate thread
  - Why: MinIO SDK calls are blocking and should not run directly on the event loop.
- [MinIO Python SDK](https://github.com/minio/minio-py)
  - Specific section: object upload patterns and SDK usage
  - Why: Confirms the current project already uses the MinIO Python SDK directly and should extend that integration rather than introduce a new storage client.
- [Amazon S3 Multipart Upload Overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)
  - Specific section: multipart upload lifecycle and part ordering
  - Why: MinIO is S3-compatible; this is the canonical reference for multipart semantics, part numbering, and finalization behavior.

### Patterns to Follow

**Router Pattern**

- Routers perform validation and ownership checks locally, then delegate to services.
- Current upload routers both:
  - validate extension
  - allocate `uuid`
  - construct `object_name`
  - upload to storage
  - commit metadata
  - schedule indexing

**Error Handling Pattern**

- `rag_collections.py:194-214` rolls back, then attempts to reload the metadata row and mark it `FAILED`.
- `projects.py:131-134` rolls back and returns `503`.
- Preserve these semantics; do not silently swallow upload failures.

**Logging Pattern**

- Use `structlog.get_logger(__name__)` or `structlog.get_logger()`.
- Log structured fields like `object_name`, `rag_collection_id`, `project_id`, and `file_name`.
- Keep infrastructure logging in services, not routers, where possible.

**Storage Integration Pattern**

- `StorageService` is a singleton service object instantiated at module import.
- Bucket existence is lazily ensured once through `_ensure_bucket()`.
- The service already centralizes MinIO access; the upload refactor should extend this class, not duplicate MinIO calls inside routers.

**Anti-Patterns to Remove**

- `await file.read()` for the whole payload in router code.
- `io.BytesIO(data)` around the entire file payload in `StorageService.upload_file(...)`.
- `async def` wrappers that directly call blocking SDK methods without thread offload.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Define the streaming upload contract and isolate blocking MinIO calls from the event loop.

**Tasks:**

- Design a storage-layer API that accepts a file-like stream plus content metadata.
- Decide whether the current max-file-size policy stays constant or becomes settings-driven.
- Keep worker/index-job contracts unchanged.

### Phase 2: Core Implementation

Move upload handling from eager buffering to stream-based MinIO writes.

**Tasks:**

- Add stream-based upload support to `StorageService`.
- Update RAG collection uploads to use streaming storage writes.
- Update project uploads to use the same storage path.
- Ensure metadata size fields come from stream metadata or explicit size probing without full buffering.

### Phase 3: Integration

Reconnect router logic, preserve response shapes, and keep downstream indexing behavior stable.

**Tasks:**

- Keep `RagFileUploadResponse` and project upload response unchanged.
- Preserve queue scheduling order: upload first, commit metadata, then enqueue.
- Keep `worker-indexjob` untouched for the first iteration.

### Phase 4: Testing & Validation

Prove the upload path no longer depends on full-memory buffering and still schedules indexing correctly.

**Tasks:**

- Add router tests for both upload entrypoints.
- Add storage helper tests around streaming uploads and exception handling.
- Run existing indexing orchestration tests and upload API tests.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE services/rag-service/app/services/storage.py

- **IMPLEMENT**: Add a stream-oriented upload method, for example `upload_stream(...)` or `upload_upload_file(...)`, that accepts a file-like object, explicit `length`, and `content_type`, and calls blocking MinIO upload logic via `asyncio.to_thread(...)`.
- **PATTERN**: Reuse endpoint normalization and bucket-check behavior from `services/rag-service/app/services/storage.py:17-50`.
- **IMPORTS**: `asyncio`, `BinaryIO`/`IO` typing as needed, existing `Minio`, `S3Error`, `settings`.
- **GOTCHA**: Rewind any inspected stream before uploading; do not consume the file in routers and then hand MinIO an exhausted stream.
- **VALIDATE**: `uv run --project services/rag-service python -c "from app.services.storage import storage_service; print(hasattr(storage_service, 'upload_stream'))"`

### UPDATE services/rag-service/app/routers/rag_collections.py

- **IMPLEMENT**: Replace whole-file buffering in `upload_rag_file(...)` with stream-based upload through the new storage helper.
- **PATTERN**: Preserve object-name construction and failure-path semantics from `services/rag-service/app/routers/rag_collections.py:161-214`.
- **IMPORTS**: New storage helper signature only; avoid introducing direct MinIO SDK usage here.
- **GOTCHA**: Current code computes `file_size` from `len(content)`; replace this with `UploadFile.size` when available or a safe seek/tell/rewind fallback.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py -q`

### UPDATE services/rag-service/app/routers/projects.py

- **IMPLEMENT**: Refactor `upload_project_file(...)` to match the new stream-based storage path used by `rag_collections.py`.
- **PATTERN**: Mirror the post-upload flow in `services/rag-service/app/routers/projects.py:91-134` - create `ProjectNode`, upload, commit, then schedule indexing.
- **IMPORTS**: New storage helper signature only.
- **GOTCHA**: Keep project and RAG upload endpoints behaviorally aligned; do not let one remain buffered while the other streams.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_projects_api.py -q`

### UPDATE services/rag-service/app/config.py

- **IMPLEMENT**: Only if needed, add upload-related settings such as multipart threshold, multipart part size, upload worker-thread count, or upload max size.
- **PATTERN**: Follow the existing `BaseSettings` field style from `services/rag-service/app/config.py:33-53`.
- **IMPORTS**: `Field` only if aliases/defaults are needed.
- **GOTCHA**: Do not introduce configuration that is unused by the first implementation; every new setting should drive real code paths.
- **VALIDATE**: `uv run --project services/rag-service python -c "from app.config import settings; print(settings.s3_bucket)"`

### CREATE services/rag-service/tests/test_storage_service.py

- **IMPLEMENT**: Add unit tests for the new stream upload helper, including successful upload, stream rewind after size probing, and MinIO exception propagation.
- **PATTERN**: Use `AsyncMock`/patching style consistent with `services/rag-service/tests/test_index_job_service.py:43-139`.
- **IMPORTS**: `io`, `pytest`, `AsyncMock` or monkeypatch helpers, `StorageService`.
- **GOTCHA**: Mock blocking MinIO client methods at the service boundary; do not require a real MinIO server for unit tests.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_storage_service.py -q`

### CREATE services/rag-service/tests/test_projects_api.py

- **IMPLEMENT**: Add router tests for project file uploads covering success, invalid extension, oversized file, and storage failure.
- **PATTERN**: Mirror app composition and dependency override style from `services/rag-service/tests/test_rag_collections_api.py:21-78`.
- **IMPORTS**: `FastAPI`, `ASGITransport`, `AsyncClient`, async DB session fixtures, `AsyncMock`.
- **GOTCHA**: Patch `storage_service` and `index_job_service` at the router module level just like the existing RAG collection tests do.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_projects_api.py -q`

### UPDATE services/rag-service/tests/test_rag_collections_api.py

- **IMPLEMENT**: Expand the existing test to assert the router uses the new storage helper without reading the full body into bytes-oriented APIs.
- **PATTERN**: Keep dependency overrides and `AsyncMock` patch style unchanged.
- **IMPORTS**: Only new helper mock names if the storage API changes.
- **GOTCHA**: Preserve the current contract that a successful upload response returns `status="pending"` and a non-null `index_job_id`.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py -q`

### VERIFY worker contract remains unchanged

- **IMPLEMENT**: Re-run worker indexing tests and confirm no changes are required to `worker/main.py` or `worker/services/storage_client.py`.
- **PATTERN**: Preserve `execute_document_index_job(...)` behavior from `worker/main.py:428-496`.
- **IMPORTS**: None.
- **GOTCHA**: The worker still depends on the original uploaded object existing in MinIO at `job.storage_path`; do not convert this feature into an inline indexing flow.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_main.py -q -k document_index_job`

### ADD follow-on architecture note for storage-service parity

- **IMPLEMENT**: Document that `services/storage-service/app/main.py:70-91` still uses eager buffering and should be aligned in a separate follow-on if the proxy upload route becomes performance-critical.
- **PATTERN**: Keep the note concise and factual, similar to architecture notes already used in `.agents/plans/` and `docs/`.
- **IMPORTS**: None.
- **GOTCHA**: Do not expand scope by refactoring `storage-service` in the first pass unless tests or runtime usage prove it is on the hot path.
- **VALIDATE**: `rg -n "storage-service parity|eager buffering" .agents/plans docs`

---

## TESTING STRATEGY

The service already uses `pytest`, `pytest-asyncio`, lightweight SQLite-backed router tests, and module-level service patching. This feature should stay inside those patterns.

### Unit Tests

- `test_storage_service.py`
  - stream upload success path
  - thread-offloaded MinIO upload invocation
  - stream rewind after size probing
  - MinIO upload exception propagation
- `test_index_job_service.py`
  - keep existing scheduling tests green to ensure upload refactor does not affect queue behavior

### Integration Tests

- `test_rag_collections_api.py`
  - upload a file and verify pending response plus `index_job_id`
  - upload invalid extension and confirm `400`
  - simulate storage failure and confirm `503` plus failed metadata semantics
- `test_projects_api.py`
  - upload a project file and verify indexing is scheduled
  - invalid extension
  - oversized file
  - storage failure rollback

### Edge Cases

- upload where `UploadFile.size` is unavailable and size must be derived safely
- special characters in `file.filename`
- empty file upload
- upload that fails after metadata object is created but before commit
- upload near the configured size ceiling
- concurrent uploads to both project and RAG endpoints
- unchanged worker path: uploaded object must remain downloadable from MinIO for later indexing

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and feature correctness.

### Level 1: Syntax & Style

- `uv run --project services/rag-service python -m compileall services/rag-service/app`
- `uv run --project services/rag-service ruff check services/rag-service/app services/rag-service/tests`

### Level 2: Unit Tests

- `uv run --project services/rag-service pytest services/rag-service/tests/test_storage_service.py -q`
- `uv run --project services/rag-service pytest services/rag-service/tests/test_index_job_service.py -q`

### Level 3: Integration Tests

- `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py services/rag-service/tests/test_projects_api.py -q`
- `uv run --project worker pytest worker/tests/test_main.py -q -k document_index_job`

### Level 4: Manual Validation

1. Start `postgres`, `minio`, `rabbitmq`, `rag-service`, and `worker-indexjob`.
2. Create a RAG collection.
3. Upload a large supported file through `POST /api/rags/{rag_id}/files/upload`.
4. Confirm service memory stays stable compared with the old buffering path.
5. Confirm the uploaded object exists in MinIO.
6. Confirm a `DocumentIndexJob` is created and consumed by `worker-indexjob`.
7. Repeat the same test for `POST /api/projects/{project_id}/files/upload`.

### Level 5: Additional Validation (Optional)

- `rg -n "await file.read\\(|BytesIO\\(data\\)|len\\(content\\)" services/rag-service/app`
- `rg -n "upload_stream|to_thread|multipart" services/rag-service/app services/rag-service/tests`

---

## ACCEPTANCE CRITERIA

- [ ] `rag-service` no longer reads the full upload body into memory in `rag_collections.py` or `projects.py`.
- [ ] MinIO uploads are performed through a stream-based storage helper.
- [ ] Blocking MinIO SDK upload work is offloaded from the event loop thread.
- [ ] Existing upload response shapes remain backward compatible.
- [ ] Existing index scheduling behavior remains unchanged after successful upload.
- [ ] Worker indexing still downloads the original file from MinIO using `job.storage_path`.
- [ ] New storage helper tests pass.
- [ ] RAG and project upload router tests pass.
- [ ] Existing index job service tests pass without behavioral regressions.
- [ ] The implementation leaves client-side resumable uploads and storage-service parity explicitly out of scope or documented as follow-on work.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full relevant test suite passes
- [ ] No linting or syntax errors remain
- [ ] Manual validation confirms upload -> storage -> index flow still works
- [ ] Acceptance criteria all met
- [ ] Follow-on note for storage-service parity is documented

---

## NOTES

- This plan deliberately avoids changing the worker indexing contract. The worker should still download the original object from MinIO and index it asynchronously.
- This plan also deliberately avoids client-side resumable uploads in the first pass. The goal is server-side streaming/multipart safety first.
- If product requirements later demand truly resumable uploads, that becomes a separate feature requiring upload-session state, part tracking, and explicit finalize/cancel endpoints.
- The current `storage-service` proxy has the same buffering anti-pattern, but `rag-service` currently talks to MinIO directly; treat proxy parity as a follow-on unless scope is intentionally widened.
- Confidence Score: 8/10 that execution will succeed on first attempt.
