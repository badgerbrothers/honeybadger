# Feature: Support 1GiB RAG Upload And Processing

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Raise the effective RAG upload ceiling from the current layered `50MB`/`60m` limits to `1GiB`, and make the downstream indexing path capable of processing large text-like knowledge files without full-memory buffering.

Today, the `rag-service` upload path already streams `UploadFile.file` into MinIO, so the transport-side change is partly solved. The blocking issue is the rest of the ingestion pipeline:

- gateway still enforces a small request-body cap
- frontend still rejects files above `50MB`
- worker download logic reads the full MinIO object into memory
- text and markdown parsers materialize the entire file as one string
- indexing core assumes parse -> whole text -> chunk -> embed

The implementation should preserve the existing `DocumentIndexJob` asynchronous contract:

- upload original file to object storage
- persist file metadata
- enqueue index job
- let `worker-indexjob` download and index the object

This feature is not a simple constant bump. It is a large-file ingestion refactor with explicit scope control.

## User Story

As a user uploading large RAG knowledge files
I want the system to accept and process files up to 1GiB
So that large documentation sets can be ingested without manual splitting or out-of-memory failures

## Problem Statement

The current codebase has inconsistent and misleading upload limits:

- Nginx currently allows only `60m`
- frontend validation still blocks files above `50MB`
- `rag-service` route validation still rejects files above `50MB`
- worker download logic uses `response.read()`, loading the full object into RAM
- text parsers use `read_text()` and return one large `text` payload

This means that even if the upload threshold is increased, the system still cannot safely process `1GiB` files end-to-end. Raising only the request size would shift failures from the API edge to the worker/indexing path.

There is also an architectural boundary to keep explicit:

- `RAG` collection uploads (`/api/rags/...`) already upload directly to MinIO in a stream-friendly way
- `project-service` uploads (`/api/projects/...`) still buffer into memory and proxy via `storage-service`

This plan assumes the immediate product need is `RAG collection` large-file support. Project attachment uploads should either keep their current lower limit or be separately refactored before sharing the same `1GiB` claim in the UI.

## Solution Statement

Implement `1GiB` support as an end-to-end RAG ingestion change with two layers:

1. Transport and validation layer
- raise gateway and backend caps for the RAG route
- split frontend validation so RAG uploads can move to `1GiB` without falsely advertising the same capability for project uploads
- make the RAG upload limit settings-driven instead of hardcoded

2. Processing layer
- replace worker full-memory object download with streaming download to a temp file
- refactor indexing/parsing for text-like formats so large files are chunked incrementally instead of first materializing a 1GiB Python string
- keep the original object in MinIO and preserve the asynchronous `DocumentIndexJob` workflow

Recommended scope boundary:

- In scope: `.txt`, `.md`, `.markdown`, `.json`, `.csv` RAG files
- Explicit decision required for `.pdf`: either keep a lower cap, or accept that current parser behavior remains high-risk for very large PDFs

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: High
**Primary Systems Affected**: `frontend`, `nginx`, `services/rag-service`, `worker`, `shared/rag`, `docker-compose`
**Dependencies**: FastAPI `UploadFile`, MinIO Python SDK, Python streaming IO, `asyncio.to_thread`, structlog, existing RabbitMQ-backed `DocumentIndexJob` flow

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `frontend/src/lib/fileUpload.ts` (lines 3-74) - Current shared frontend size limit and file-type validation. This currently affects both RAG and project uploads, so the implementation must decide whether to split limits by upload surface.
- `frontend/src/features/rag/RagDetailPage.tsx` (lines 176-227) - RAG page file picker and upload error handling.
- `nginx/nginx.conf` (lines 29-124) - Current gateway routing and `client_max_body_size 60m`; this is the first hard request-body bottleneck.
- `services/rag-service/app/routers/rag_collections.py` (lines 29-30, 150-228) - Current RAG upload limit, extension whitelist, metadata creation, MinIO upload, and index job scheduling.
- `services/rag-service/app/services/storage.py` (lines 56-101) - Existing stream-friendly MinIO upload implementation using `put_object(...)` and `asyncio.to_thread(...)`; this is the pattern to keep for the upload leg.
- `services/rag-service/app/config.py` (lines 27-55) - Current settings style and existing object-storage multipart config.
- `worker/main.py` (lines 428-500) - Document index job execution. This currently downloads the full object into memory and only then writes it to disk.
- `worker/services/storage_client.py` (lines 44-51) - Current full-memory MinIO download helper using `response.read()`.
- `worker/rag/indexer.py` (lines 14-64) - Current parser registry and indexing flow; still parse -> full text -> chunks -> embeddings.
- `shared/rag/indexing_core.py` (lines 36-86) - Core abstraction that currently assumes a full parsed `text` string exists in memory.
- `shared/rag/parsers/txt_parser.py` (lines 14-41) - Uses `read_text()` and returns one large string; not viable for `1GiB`.
- `shared/rag/parsers/markdown_parser.py` (lines 17-45) - Uses `read_text()` and HTML conversion over the entire file; not viable for `1GiB`.
- `shared/rag/parsers/pdf_parser.py` (lines 16-47) - Page-wise extraction but still joins all text into one giant string; format policy must be revisited before claiming `1GiB` PDF support.
- `docker-compose.yml` (lines 189-230, 319-358, 360-379) - Container memory limits and service topology. `rag-service` and `worker-indexjob` both currently run under `1g`, so a 1GiB file cannot safely be fully materialized in memory.
- `services/project-service/app/routers/projects.py` (lines 100-173) - Current project upload path still uses `await file.read()` and should not silently inherit the new RAG limit.
- `services/storage-service/app/main.py` (lines 78-126) - Storage proxy still eagerly buffers upload and download; useful to document as out-of-scope or follow-on if product later demands `1GiB` project uploads too.
- `services/rag-service/tests/test_rag_collections_api.py` (entire file) - Existing async router test style for RAG uploads.
- `services/rag-service/tests/test_storage_service.py` (entire file) - Existing storage helper unit test style.
- `worker/tests/test_main.py` (lines 479-548) - Existing index-job execution tests and failure-state assertions.
- `worker/tests/test_indexer.py` (entire file) - Current indexer test style and mocking approach.
- `services/project-service/tests/test_project_rag_binding_api.py` (entire file) - Current project-service API test composition pattern.
- `docs/rag-upload-followups.md` (entire file) - Existing architecture note about streaming upload parity and storage-service buffering concerns.
- `CLAUDE.md` (lines 3-67) - Current stack and service layout, useful to keep service boundaries consistent.

### New Files to Create

- `worker/tests/test_storage_client.py` - Unit tests for streaming download-to-path behavior and resource cleanup.
- `worker/tests/test_streaming_indexing_core.py` - Focused tests for incremental parse/chunk behavior on large text-like inputs.
- `services/project-service/tests/test_project_upload_limits_api.py` - Only if the implementation explicitly changes project-upload validation behavior or splits frontend/backend limits by surface.
- `docs/1g-rag-upload-decisions.md` - Optional short ADR-style note if the implementation introduces per-format limits such as `1GiB` for text-like files and a smaller cap for PDFs.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI Request Files](https://fastapi.tiangolo.com/tutorial/request-files/)
  - Specific section: `UploadFile`
  - Why: Confirms why `UploadFile` is preferred for large request bodies and how to avoid full in-memory buffering at the API layer.
- [FastAPI UploadFile Reference](https://fastapi.tiangolo.com/reference/uploadfile/)
  - Specific section: `.file`, `.size`, `.read()`, `.seek()`
  - Why: Needed for correct size inspection and safe stream reuse.
- [Python asyncio `to_thread`](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
  - Specific section: running blocking IO in a worker thread
  - Why: Current MinIO client usage is blocking and must stay off the event loop.
- [NGINX `client_max_body_size`](https://nginx.org/en/docs/http/ngx_http_core_module.html#client_max_body_size)
  - Specific section: maximum allowed size of the client request body
  - Why: This is the first transport cap that must be raised for `1GiB` uploads.
- [Amazon S3 Multipart Upload Overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)
  - Specific section: multipart upload lifecycle
  - Why: MinIO is S3-compatible; this is the canonical reference for large object upload semantics.
- [HTTPX Async Support](https://www.python-httpx.org/async/)
  - Specific section: streaming responses and async clients
  - Why: Useful if implementation later needs streaming proxy behavior or non-buffered service-to-service transfer.
- [Docker Compose File Reference](https://docs.docker.com/compose/compose-file/)
  - Specific section: service resource constraints
  - Why: Current container memory limits directly constrain whether `1GiB` objects can be processed safely.

### Patterns to Follow

**Naming Conventions:**

- Constants are uppercase snake_case in routers and frontend helpers: `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`, `KNOWLEDGE_FILE_MAX_SIZE`.
- Service instances are module singletons: `storage_service = StorageService()`.
- Settings live in `BaseSettings` classes and are exposed through `settings`.

**Error Handling:**

- Router validation uses `HTTPException` with explicit status codes.
- Upload failures in `rag_collections.py` roll back and log structured context before returning `503`.
- Worker failure classification uses dedicated error-code mapping in `worker/main.py:155-180`.

**Logging Pattern:**

- Use `structlog.get_logger(__name__)` or `structlog.get_logger()`.
- Include structured identifiers such as `rag_collection_id`, `object_name`, `file_name`, `job_id`, `error_code`, `failed_step`.

**Testing Pattern:**

- API tests use `FastAPI()` + router include + dependency overrides + SQLite temp DB.
- Service tests prefer `AsyncMock`, `Mock`, and monkeypatching module-level singletons.
- Worker tests patch imported modules at the `worker.main` boundary rather than hitting real infrastructure.

**Other Relevant Patterns:**

- `services/rag-service/app/services/storage.py` already demonstrates the desired upload pattern:
  - explicit content length
  - direct file-like stream handoff to MinIO
  - blocking client work inside `asyncio.to_thread(...)`
- `worker/main.py` currently writes a downloaded object to `worker_tmp/rag/...`; reuse this temp-file pattern, but stream directly into the destination file instead of first buffering bytes.

---

## IMPLEMENTATION PLAN

### Phase 1: Scope And Limit Model

Turn the implicit mix of `50MB`, `60m`, and container-memory constraints into an explicit large-file policy.

**Tasks:**

- Define RAG-specific size settings instead of relying on shared hardcoded constants.
- Decide whether `1GiB` applies to all allowed formats or only text-like formats.
- Decide whether project uploads stay at their current lower limit in this phase.

### Phase 2: Transport And Validation

Raise the request-body ceiling only where the downstream pipeline can actually support it.

**Tasks:**

- Increase gateway limit for RAG uploads.
- Update frontend RAG validation to `1GiB`.
- Update `rag-service` limit checks to settings-driven values.
- If project uploads remain out of scope, split shared frontend validation so conversation/project uploads do not falsely advertise `1GiB`.

### Phase 3: Worker Streaming Download

Eliminate the current full-memory object download path.

**Tasks:**

- Add streaming MinIO download-to-path support in `worker/services/storage_client.py`.
- Update `execute_document_index_job(...)` to stream directly into the temp file.
- Preserve the existing index-job state machine and storage-path contract.

### Phase 4: Incremental Parsing And Chunking

Refactor the text ingestion path so processing does not require a full 1GiB string in memory.

**Tasks:**

- Introduce incremental parsing/chunk generation for text-like formats.
- Update indexing core to work on chunk iterators or bounded windows instead of a monolithic parsed `text` string.
- Re-evaluate PDF support separately rather than silently claiming `1GiB` parity.

### Phase 5: Testing And Validation

Prove that the system can accept and process large text-like files within bounded memory.

**Tasks:**

- Add targeted worker download and streaming indexing tests.
- Update RAG upload API tests to reflect the new limit behavior.
- Add manual validation with a large generated markdown file.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE services/rag-service/app/config.py

- **IMPLEMENT**: Add settings-driven RAG upload limit fields, for example `rag_upload_max_bytes`, and optionally format-specific caps such as `rag_pdf_upload_max_bytes` if the final design does not support `1GiB` PDFs.
- **PATTERN**: Follow the existing `BaseSettings` field style in `services/rag-service/app/config.py:33-55`.
- **IMPORTS**: Existing `Field` and `AliasChoices` patterns only if aliases are needed.
- **GOTCHA**: Do not leave `MAX_FILE_SIZE` hardcoded in routers once settings exist; one source of truth is required.
- **VALIDATE**: `uv run --project services/rag-service python -c "from app.config import settings; print(settings.model_dump())"`

### UPDATE services/rag-service/app/routers/rag_collections.py

- **IMPLEMENT**: Replace hardcoded `MAX_FILE_SIZE = 50 * 1024 * 1024` with settings-driven values and explicit format-policy validation.
- **PATTERN**: Preserve the ownership check, object-name generation, metadata persistence, and failure handling from `services/rag-service/app/routers/rag_collections.py:150-228`.
- **IMPORTS**: `from app.config import settings` plus any small helper extracted for limit calculation.
- **GOTCHA**: Upload validation must stay aligned with actual downstream processing support. Do not allow `1GiB` for a format that still requires whole-file parsing unless you deliberately accept that risk and document it.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py -q`

### UPDATE frontend/src/lib/fileUpload.ts

- **IMPLEMENT**: Split shared upload-size policy into explicit surfaces, for example `RAG_KNOWLEDGE_FILE_MAX_SIZE` and `PROJECT_FILE_MAX_SIZE`, plus matching validation helpers.
- **PATTERN**: Reuse the existing extension and error-message helper structure in `frontend/src/lib/fileUpload.ts:3-74`.
- **IMPORTS**: Keep `ApiError`-based error formatting.
- **GOTCHA**: Today this file is shared by RAG and conversation uploads. If you simply change the one constant to `1GiB`, the UI will claim project uploads can also handle `1GiB`, which is false with the current `project-service` path.
- **VALIDATE**: `npm run type-check`

### UPDATE frontend/src/features/rag/RagDetailPage.tsx

- **IMPLEMENT**: Use the RAG-specific validation helper and surface the new `1GiB` policy in the error messages.
- **PATTERN**: Keep the existing hidden-input upload flow from `frontend/src/features/rag/RagDetailPage.tsx:188-206`.
- **IMPORTS**: RAG-specific helpers from `frontend/src/lib/fileUpload.ts`.
- **GOTCHA**: Keep upload errors human-readable; do not regress to raw HTML or generic network errors.
- **VALIDATE**: `npm run lint`

### UPDATE nginx/nginx.conf

- **IMPLEMENT**: Raise `client_max_body_size` for the gateway to exceed `1GiB` safely, and review proxy timeouts for long-running uploads.
- **PATTERN**: Preserve existing route layout in `nginx/nginx.conf:47-124`.
- **IMPORTS**: None.
- **GOTCHA**: If the configured body limit equals exactly `1g`, any multipart framing overhead can still trip the gateway. Leave headroom above the advertised logical file-size limit.
- **VALIDATE**: `docker compose up -d --build --no-deps api-gateway`

### UPDATE worker/services/storage_client.py

- **IMPLEMENT**: Replace `download_file(object_name) -> bytes` with a streaming helper such as `download_to_path(object_name, destination_path)` that reads the MinIO response incrementally and writes to disk.
- **PATTERN**: Preserve endpoint normalization and client lazy initialization from `worker/services/storage_client.py:12-42`.
- **IMPORTS**: `Path` and buffered file-writing helpers as needed.
- **GOTCHA**: Ensure the MinIO response is always `close()`d and `release_conn()` is called on both success and failure.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_storage_client.py -q`

### UPDATE worker/main.py

- **IMPLEMENT**: Refactor `execute_document_index_job(...)` so the worker streams the object directly to `worker_tmp/rag/...` instead of storing it first in `file_bytes`.
- **PATTERN**: Preserve the surrounding status transitions and error-code mapping from `worker/main.py:428-500`.
- **IMPORTS**: Updated storage client helper only; avoid rewriting the job state machine.
- **GOTCHA**: The `download_file` -> `write_bytes` sequence is not the only memory problem, but it is the first mandatory change for large files.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_main.py -q -k document_index_job`

### REFACTOR shared/rag/indexing_core.py

- **IMPLEMENT**: Introduce an incremental ingestion contract for text-like files. Recommended direction: allow parsers to yield normalized text segments or chunk-ready blocks, and let indexing core batch/chunk/embed incrementally instead of requiring one full parsed `text` string.
- **PATTERN**: Preserve the existing separation of parse/chunk/embed responsibilities in `shared/rag/indexing_core.py:36-86`, but change the contract so large-file processing is bounded-memory.
- **IMPORTS**: `Iterator`/`Iterable` typing, small helper abstractions only.
- **GOTCHA**: A streaming download alone is not enough. `parse_document()` currently returns a monolithic string, which still defeats `1GiB` processing.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_indexer.py -q`

### UPDATE shared/rag/parsers/txt_parser.py

- **IMPLEMENT**: Add an incremental parse path for large text files. Recommended direction: iterate line-by-line or fixed-size windows and yield normalized text blocks instead of one huge `text`.
- **PATTERN**: Preserve encoding fallback behavior from `shared/rag/parsers/txt_parser.py:18-27`.
- **IMPORTS**: Standard file IO only.
- **GOTCHA**: `read_text()` is the exact anti-pattern blocking `1GiB` support; remove it from the large-file path.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_txt_parser.py -q`

### UPDATE shared/rag/parsers/markdown_parser.py

- **IMPLEMENT**: Add an incremental markdown-friendly path. Recommended direction: process the file in bounded sections and normalize markdown to text without converting the entire document into one HTML string in memory.
- **PATTERN**: Preserve current metadata semantics where practical, but allow metadata to become approximate or streaming-derived for large files.
- **IMPORTS**: Existing `markdown` library only if it remains tractable at block level; otherwise document the replacement approach before coding.
- **GOTCHA**: Full-file `markdown.markdown(md_content)` is not viable for `1GiB`. If the library cannot be used incrementally, choose a simpler block-normalization approach for large-file mode.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_markdown_parser.py -q`

### UPDATE shared/rag/parsers/pdf_parser.py

- **IMPLEMENT**: Make an explicit product decision for large PDFs. Either keep PDF on a smaller cap with clear validation, or add bounded-memory extraction if the library can support it.
- **PATTERN**: Preserve page-wise extraction semantics from `shared/rag/parsers/pdf_parser.py:25-47`.
- **IMPORTS**: Existing `pypdf` only unless a new parser library is formally chosen.
- **GOTCHA**: Do not claim universal `1GiB` support while PDF parsing still joins the entire document text into one string.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_pdf_parser.py -q`

### UPDATE worker/rag/indexer.py

- **IMPLEMENT**: Wire the new incremental parse/chunk contract into `DocumentIndexer`, preserving parser registration and DB write behavior.
- **PATTERN**: Keep parser registry ownership inside `worker/rag/indexer.py:17-24` and preserve `_store_chunks(...)` behavior.
- **IMPORTS**: Updated indexing-core/parsers only.
- **GOTCHA**: `DocumentIndexer` currently registers only `.txt`, `.md`, `.markdown`, `.pdf`. If product expects `.json` and `.csv` to join the `1GiB` plan, parser coverage must be fixed as part of this implementation or explicitly excluded.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_indexer.py -q`

### CREATE worker/tests/test_storage_client.py

- **IMPLEMENT**: Add unit tests for streaming MinIO download-to-path behavior, including resource cleanup on success and failure.
- **PATTERN**: Match `AsyncMock` and patch style already used in `worker/tests/test_main.py:479-548`.
- **IMPORTS**: `pytest`, `AsyncMock`, `Mock`, `Path`, `tempfile` or `tmp_path`.
- **GOTCHA**: Do not require a real MinIO instance; mock the response object's `read`, `stream`, `close`, and `release_conn` behavior.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_storage_client.py -q`

### CREATE worker/tests/test_streaming_indexing_core.py

- **IMPLEMENT**: Add focused tests proving that large text-like inputs can be incrementally parsed and chunked without constructing one giant `text` string.
- **PATTERN**: Reuse lightweight unit-test structure from `worker/tests/test_indexer.py` and parser tests.
- **IMPORTS**: `pytest`, mocks, temp files.
- **GOTCHA**: Assert behavioral properties, not just output equality. For example: parser does not call full-file `read_text()`, chunk generation is incremental, embedding batches remain bounded.
- **VALIDATE**: `uv run --project worker pytest worker/tests/test_streaming_indexing_core.py -q`

### UPDATE services/rag-service/tests/test_rag_collections_api.py

- **IMPLEMENT**: Add coverage for the new `1GiB` validation behavior, including any format-specific caps.
- **PATTERN**: Keep the existing router-override style from `services/rag-service/tests/test_rag_collections_api.py:35-78`.
- **IMPORTS**: Existing test helpers only.
- **GOTCHA**: Make the tests assert the configured limit source, not a stale literal `50MB`.
- **VALIDATE**: `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py -q`

### OPTIONAL UPDATE services/project-service path or explicitly freeze its lower cap

- **IMPLEMENT**: Choose one of two explicit outcomes:
- **IMPLEMENT**: Option A, recommended for this phase: keep project uploads on the existing lower cap and update frontend validation so only RAG uploads expose `1GiB`.
- **IMPLEMENT**: Option B, larger scope: refactor `services/project-service/app/routers/projects.py` and `services/storage-service/app/main.py` to streaming upload semantics before raising their limits.
- **PATTERN**: If you choose Option B, mirror the stream-based MinIO upload style already present in `services/rag-service/app/services/storage.py:87-101`.
- **IMPORTS**: Depends on chosen option.
- **GOTCHA**: Do not accidentally claim product-wide `1GiB` upload support while project uploads still use `await file.read()` plus HTTP proxy buffering.
- **VALIDATE**: `uv run --project services/project-service pytest services/project-service/tests -q`

### ADD architecture note for scope boundary

- **IMPLEMENT**: Document whether `1GiB` support is RAG-only in phase one, and document the chosen PDF policy.
- **PATTERN**: Keep it short and factual, similar to `docs/rag-upload-followups.md`.
- **IMPORTS**: None.
- **GOTCHA**: This note is mandatory if any route, format, or UI surface remains below the `1GiB` ceiling.
- **VALIDATE**: `rg -n "1GiB|PDF|project uploads|scope" docs .agents/plans`

---

## TESTING STRATEGY

This feature crosses API, worker, and shared indexing layers. Testing must prove both correctness and memory-safe architecture direction.

### Unit Tests

- `worker/tests/test_storage_client.py`
  - streamed object download to local file
  - response cleanup on success/failure
  - no full `bytes` materialization contract
- `worker/tests/test_streaming_indexing_core.py`
  - incremental parse/chunk behavior for large text-like inputs
  - bounded embedding batch size
- Existing parser tests
  - txt parser
  - markdown parser
  - pdf parser if still supported under the new policy

### Integration Tests

- `services/rag-service/tests/test_rag_collections_api.py`
  - successful upload under new configured limit
  - invalid extension still rejected
  - oversized upload rejected according to new policy
  - storage failure still returns `503`
- `worker/tests/test_main.py`
  - `execute_document_index_job(...)` success path after streaming-download refactor
  - failure states remain correct

### Edge Cases

- upload size exactly at the configured `1GiB` ceiling
- multipart overhead slightly above file size at gateway layer
- upload of empty file
- markdown file with extremely long lines
- text file with encoding fallback
- worker crash after partial download to temp file
- cleanup of partially written temp files
- large-file parse mode that spans chunk boundaries cleanly
- `.pdf` files above the safe parser threshold if PDF remains partially unsupported
- `.json` / `.csv` alignment with parser registry and whitelist

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and feature correctness.

### Level 1: Syntax & Style

- `uv run --project services/rag-service python -m compileall services/rag-service/app`
- `uv run --project worker python -m compileall worker shared`
- `uv run --project services/rag-service ruff check services/rag-service/app services/rag-service/tests`
- `uv run --project worker ruff check worker shared`
- `npm run type-check`
- `npm run lint`

### Level 2: Unit Tests

- `uv run --project worker pytest worker/tests/test_storage_client.py -q`
- `uv run --project worker pytest worker/tests/test_streaming_indexing_core.py -q`
- `uv run --project worker pytest worker/tests/test_txt_parser.py worker/tests/test_markdown_parser.py worker/tests/test_pdf_parser.py -q`
- `uv run --project worker pytest worker/tests/test_indexer.py -q`

### Level 3: Integration Tests

- `uv run --project services/rag-service pytest services/rag-service/tests/test_rag_collections_api.py services/rag-service/tests/test_storage_service.py -q`
- `uv run --project worker pytest worker/tests/test_main.py -q -k document_index_job`
- `uv run --project services/project-service pytest services/project-service/tests -q`

### Level 4: Manual Validation

1. Start `postgres`, `redis`, `minio`, `rabbitmq`, `rag-service`, `worker-indexjob`, `api-gateway`, and `frontend`.
2. Create a RAG collection.
3. Generate a large markdown file, for example `800MB` to `1GiB`, locally.
4. Upload it through the RAG page.
5. Confirm the browser request succeeds and Nginx does not return `413`.
6. Confirm MinIO contains the uploaded object.
7. Confirm a `DocumentIndexJob` is created.
8. Confirm the worker downloads to `worker_tmp/rag/...` without allocating a giant `bytes` payload.
9. Confirm indexing completes for text-like formats or fails with an explicit, documented policy for formats intentionally capped lower.
10. Confirm project upload UI still behaves consistently with the chosen scope boundary.

### Level 5: Additional Validation (Optional)

- `rg -n "50 \\* 1024 \\* 1024|60m|1GiB|rag_upload_max_bytes" frontend nginx services worker shared`
- `rg -n "response.read\\(|read_text\\(|await file.read\\(" services worker shared`
- `docker compose ps`

---

## ACCEPTANCE CRITERIA

- [ ] RAG collection uploads accept files up to the configured `1GiB` limit at the gateway, frontend, and backend validation layers.
- [ ] `rag-service` remains stream-based for MinIO uploads.
- [ ] Worker object download no longer materializes the entire file in memory before writing it locally.
- [ ] Text-like RAG files are parsed and chunked incrementally enough that `1GiB` processing is architecturally supported.
- [ ] The `DocumentIndexJob` asynchronous workflow remains unchanged from the API contract perspective.
- [ ] Any format that does not truly support `1GiB` processing, especially PDF, is explicitly limited or documented rather than silently over-promised.
- [ ] Shared frontend validation no longer falsely claims project uploads can use the RAG-only limit if project uploads stay on the old path.
- [ ] All validation commands pass with zero errors.
- [ ] Existing upload and index-job behavior has no regressions outside the intended large-file changes.
- [ ] Scope boundaries and design trade-offs are documented.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full relevant test suite passes
- [ ] No linting or type checking errors remain
- [ ] Manual validation confirms large RAG upload -> storage -> worker download -> indexing path works
- [ ] Acceptance criteria all met
- [ ] Any unsupported or partially supported formats are explicitly documented

---

## NOTES

- This plan deliberately separates `transport limit` from `processing capability`. Both must be changed for the feature to be real.
- The current `rag-service` upload path is already in good shape for large object transfer. The worker and parser pipeline are the real blockers.
- The current `project-service -> storage-service` upload path still buffers aggressively. Do not let shared frontend constants turn that into a false `1GiB` promise unless that path is refactored too.
- The current parser registry only includes `.txt`, `.md`, `.markdown`, `.pdf`, while upload whitelists also mention `.json` and `.csv`. That inconsistency should be resolved before broadening file-size claims.
- Confidence Score: 7/10 that one-pass implementation succeeds, assuming the execution agent keeps the first phase scoped to `RAG collection` large-file support and treats PDF policy as an explicit decision instead of an implicit promise.
