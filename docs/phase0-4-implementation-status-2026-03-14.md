# Phase 0-4 Implementation Status (2026-03-14)

This document records what is already implemented in code for `phase 0-4`, plus what is still pending validation.

## Completed

- Phase 0
  - Unified storage config around `s3_*` fields in backend and worker.
  - Added compatibility aliases for legacy `MINIO_*` env names.
  - Added endpoint normalization for MinIO client creation in backend and worker storage clients.
  - Added backend contract-test baseline (`unit_app_client`) and default skip behavior for DB-backed API tests when `TEST_DATABASE_URL` is not set.

- Phase 1
  - Unified worker model factory onto tool-calling providers (`openai_compat`, `anthropic_native`).
  - Unified tool protocol around `Tool` / `ToolResult` and added `metadata`.
  - Added file tools into default tool set.
  - Added optional-dependency guards:
    - Anthropic SDK missing -> explicit runtime error at call time.
    - Playwright missing -> explicit runtime error when browser tool is used.
  - Reduced import-time coupling in worker by delaying heavy imports (RAG/sandbox) to runtime paths.

- Phase 2
  - Run creation updates `Task.current_run_id`.
  - Added retry endpoint: `POST /api/tasks/{task_id}/retry`.
  - Cancel/finalization paths clear `Task.current_run_id` when applicable.
  - `TaskRunResponse` includes `logs` and `working_memory`.
  - Worker writes structured run logs and final status transitions.

- Phase 3
  - Added run event ingest endpoint: `POST /api/runs/{run_id}/events`.
  - Worker emits run events to backend through `BackendClient`.
  - Agent supports event callbacks and emits step/tool events.
  - Artifact chain extended:
    - `GET /api/artifacts/list/project/{project_id}`
    - `GET /api/artifacts/list/run/{run_id}`
    - `POST /api/artifacts/{artifact_id}/save-to-project`
  - Worker uploads artifact candidates from tool-result metadata.

- Phase 4
  - Added `DocumentIndexJob` model and status enum.
  - Added backend `rag_service` orchestration.
  - Project file upload schedules indexing jobs.
  - Worker claims and executes pending indexing jobs.
  - Worker injects retrieved project context into task execution path.
  - Added migration:
    - `backend/alembic/versions/1005_document_index_jobs_and_uuid_chunks.py`
    - includes `DocumentChunk.project_id` UUID conversion and index job table creation.

## Added Tests During This Iteration

- Backend
  - New contract suite for execution APIs:
    - `backend/tests/test_contract_execution_apis.py`
  - Updated RAG API integration tests to current request shape:
    - `backend/tests/test_api_rag.py`

- Worker
  - Extended `worker/tests/test_main.py` with:
    - index-job claim/success/failure paths
    - artifact helper event emission path
    - run success/failure path updates aligned with delayed imports

## Verified Commands

- `uv run pytest backend/tests/test_contract_projects.py backend/tests/test_contract_execution_apis.py -v`
- `uv run pytest worker/tests/test_main.py -v`
- `uv run pytest worker/tests/test_agent.py worker/tests/test_models_factory.py worker/tests/test_python_tool.py worker/tests/test_web_tool.py worker/tests/test_tools.py worker/tests/test_browser_tools.py -v`

All commands above passed in this workspace.

## Remaining Validation / Follow-up

- Apply and validate Alembic migration in a real PostgreSQL instance with representative data.
- Run end-to-end manual verification:
  - project file upload -> index job scheduling
  - worker index execution -> chunk creation
  - task run retrieval injection
  - tool-generated artifact upload
  - artifact save-to-project
- Optionally add integration tests for end-to-end chain once a stable integration DB environment is available.
