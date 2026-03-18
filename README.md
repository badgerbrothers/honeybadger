# Badgers MVP

Badgers is an AI task execution system with a domain-split microservices architecture.

- Project Service (`FastAPI`) owns project/conversation APIs
- Task Service (`FastAPI`) owns task/run/artifact APIs
- RAG Service (`FastAPI`) owns retrieval and indexing APIs
- Storage Service (`FastAPI`) provides object storage API
- API Gateway (`nginx`) is the single external API entry
- Worker is the execution plane (`Python`, Docker sandbox)
- Frontend is `Next.js`
- Queue baseline is **RabbitMQ**

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
- API Gateway: `http://localhost`
- Project Service docs: `http://localhost:8001/docs`
- Task Service docs: `http://localhost:8002/docs`
- RAG Service docs: `http://localhost:8003/docs`
- Storage Service docs: `http://localhost:8005/docs`
- MinIO console: `http://localhost:9001`

## Manual Start (Without Compose App Services)

Use this mode if you only run infra through compose.

1. Infra:

```bash
docker compose up -d postgres redis minio
```

2. Start project service:

```bash
cd services/project-service
uv sync
uv run uvicorn app.main:app --reload --port 8001
```

3. Start task service:

```bash
cd services/task-service
uv sync
uv run uvicorn app.main:app --reload --port 8002
```

4. Start rag service:

```bash
cd services/rag-service
uv sync
uv run uvicorn app.main:app --reload --port 8003
```

5. Start storage service:

```bash
cd services/storage-service
uv sync
uv run uvicorn app.main:app --reload --port 8005
```

6. Start workers:

```bash
cd worker
uv sync
set BACKEND_BASE_URL=http://localhost:8002
uv run python -m worker.worker_taskrun
uv run python -m worker.worker_indexjob
```

7. Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Current Architecture Baseline

- Task dispatch: task-service publishes TaskRun to RabbitMQ queue
- Run events: worker -> task-service ingest endpoint -> websocket fan-out
- Artifact flow: tool result -> task-service upload -> storage-service/MinIO -> project save
- RAG flow: project upload schedules indexing jobs, index worker executes jobs

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

- Services and worker use `S3_*` env names (legacy `MINIO_*` aliases are compatibility-only)
- Service HTTP client URLs:
  - `STORAGE_SERVICE_URL` (used by project/task service)
  - `RAG_SERVICE_URL` (used by project service)
- Compose internal hostnames:
  - PostgreSQL: `postgres:5432`
  - MinIO: `minio:9000`
  - Project Service: `http://project-service:8000`
  - Task Service: `http://task-service:8000`
  - RAG Service: `http://rag-service:8000`
  - API Gateway: `http://api-gateway:80`

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
