# Badgers MVP

Badgers is an AI task execution system with a modular monolith backend + independent worker architecture.

- Backend is the control plane (`FastAPI`)
- Worker is the execution plane (`Python`, Docker sandbox)
- Frontend is `Next.js`
- Current scheduler baseline is **DB polling** (Redis is reserved for future queueing)

## Prerequisites

- Docker + Docker Compose
- Python 3.11+ and `uv` (for local non-container workflows)
- Node.js 18+ (for local non-container workflows)

## Quick Start (Full Stack via Docker Compose)

1. Copy environment file:

```bash
cp .env.example .env
```

2. Fill at least:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

3. Build sandbox image used by worker-created task containers:

```bash
docker build -t badgers-sandbox:latest docker/sandbox-base
```

4. Start full stack:

```bash
docker compose up --build -d
```

5. Open:

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`

## Manual Start (Without Compose App Services)

Use this mode if you only run infra through compose.

1. Infra:

```bash
docker compose up -d postgres redis minio
```

2. Backend:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

3. Worker:

```bash
cd worker
uv sync
uv run python -m worker.main
```

4. Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Current Architecture Baseline

- Task dispatch: backend writes `TaskRun`, worker claims by DB polling
- Run events: worker -> backend ingest endpoint -> websocket fan-out
- Artifact flow: tool result -> artifact upload -> project save
- RAG flow: project upload schedules indexing jobs, worker executes indexing jobs

## Key Endpoints

- `POST /api/tasks/{task_id}/runs`
- `POST /api/tasks/{task_id}/retry`
- `POST /api/runs/{run_id}/events`
- `WS /api/runs/{run_id}/stream`
- `GET /api/projects/{project_id}/artifacts`
- `GET /api/runs/{run_id}/artifacts`
- `POST /api/artifacts/{artifact_id}/save-to-project`

## Frontend Routes (Phase 5)

- `/projects`
- `/projects/{id}`
- `/projects/{id}/artifacts`
- `/conversations/{id}`
- `/runs/{id}`

## Configuration Notes

- Backend and worker use `S3_*` env names (legacy `MINIO_*` aliases are compatibility-only)
- Compose uses service hostnames internally:
  - PostgreSQL: `postgres:5432`
  - MinIO: `minio:9000`
  - Backend from worker: `http://backend:8000`

## Testing

Backend:

```bash
cd backend
uv run pytest tests/test_contract_projects.py tests/test_contract_execution_apis.py -v
```

Worker:

```bash
cd worker
uv run pytest tests/test_main.py tests/test_agent.py tests/test_models_factory.py -v
```

## End-to-End Verification Checklist

1. Create project (`/projects`)
2. Upload file in project detail (`/projects/{id}`)
3. Create conversation from project detail and open `/conversations/{id}`
4. Add message, create task, create run
5. Open `/runs/{run_id}` and verify live events
6. Open `/projects/{id}/artifacts`, download artifact, save artifact to project
7. Verify worker picked indexing job and run retrieval uses project context
