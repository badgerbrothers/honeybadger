# RabbitMQ Migration Code Review (2026-03-18)

**Stats:**

- Files Modified: 0
- Files Added: 0
- Files Deleted: 0
- New lines: 0
- Deleted lines: 0

severity: high
file: backend/app/main.py
line: 13
issue: Backend hard-fails startup when RabbitMQ is unavailable
detail: `startup_event()` awaits `queue_service.connect()` without fallback. If RabbitMQ is down, FastAPI startup raises and the API never becomes available, so endpoints cannot return graceful queue-related errors. Reproduced with a targeted startup call where `queue_service.connect` raises `RuntimeError("rabbit down")`; exception propagates.
suggestion: Catch connect errors in startup, mark queue service as degraded/unavailable, and keep backend running. Add background reconnect or retry on publish path so `/api/tasks/{id}/runs` can return controlled 503 responses instead of taking down the whole service.

severity: high
file: backend/app/routers/projects.py
line: 112
issue: File upload can return 503 even after file metadata is committed
detail: `upload_project_file()` commits `ProjectNode` (`await db.commit()` at line 112), then calls `rag_service.schedule_indexing()`. If RabbitMQ publish fails, `schedule_indexing()` marks job failed and re-raises (`backend/app/services/rag_service.py:41-56`), which is caught by `upload_project_file()` and converted to `503 File storage service unavailable` (`projects.py:131-134`). This creates a partial-success response: client sees failure and may retry, but file already exists. Reproduced by stopping RabbitMQ: upload returned 503, while `GET /api/projects/{project_id}/files` showed the new file persisted.
suggestion: Treat indexing-queue failure as post-upload async failure, not upload failure. Return 201 for upload success and surface indexing status separately (e.g., failed `DocumentIndexJob` with retry endpoint), or split exception handling so queue publish errors do not masquerade as storage failure.

severity: medium
file: worker/worker_taskrun.py
line: 10
issue: Worker entrypoint import style is environment-fragile and breaks standard module import checks
detail: New worker entrypoints use top-level imports (`from config import ...`, `from main import ...`, `from queueing...`) instead of package-relative or `worker.*` imports. In a normal `cd worker` environment, `uv run python -c "from worker.worker_taskrun import main"` fails with `ModuleNotFoundError: No module named 'worker'` unless extra `PYTHONPATH` is injected. This increases local/dev/test fragility and hides path coupling in compose.
suggestion: Normalize imports to package-safe style (`from worker.config import settings`, `from worker.main import ...`, `from worker.queueing.rabbitmq_client import ...`) or use explicit relative imports. Add one import smoke test that runs without PYTHONPATH overrides.
