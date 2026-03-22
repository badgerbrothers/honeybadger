# Badgers MVP

Badgers is an AI task execution platform: users create tasks, workers execute them in isolated Docker sandboxes, and outputs are persisted as artifacts.

## Tech Stack

- **Backend services**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL (pgvector), structlog
- **Frontend**: Next.js 14+, React 18, TypeScript
- **Auth**: Spring Boot (JWT)
- **Task queue**: RabbitMQ (baseline)
- **Sandbox**: Docker
- **Object storage**: MinIO (S3-compatible)
- **AI/ML**: OpenAI-compatible APIs, Anthropic APIs

## Project Structure (Current Baseline)

```
badgers-mvp/
  services/                 # Domain-split services (runtime baseline)
    auth-service/           # Spring Boot auth (JWT)
    project-service/        # Projects + conversations APIs
    task-service/           # Tasks + runs + artifacts APIs
    rag-service/            # Retrieval + indexing APIs
    storage-service/        # Object storage proxy API (MinIO/S3)
  worker/                   # Execution plane (RabbitMQ consumers + sandbox + agent)
  frontend/                 # Next.js UI
  nginx/                    # API gateway (single external API entry)
  shared/                   # Shared schemas/models used across services/worker
  docker/                   # Docker configs (including sandbox base image)

Note: `backend/` still exists in the repo as legacy/compat code, but `docker-compose.yml` runs `services/*`.
```

## Commands

```bash
# Full stack (recommended)
docker compose up --build -d

# Manual start (run infra in compose, run apps locally)
docker compose up -d postgres redis minio rabbitmq

cd services/project-service
uv sync
uv run uvicorn app.main:app --reload --port 8001

cd services/task-service
uv sync
uv run uvicorn app.main:app --reload --port 8002

cd services/rag-service
uv sync
uv run uvicorn app.main:app --reload --port 8003

cd services/storage-service
uv sync
uv run uvicorn app.main:app --reload --port 8005

cd worker
uv sync
uv run python -m worker.worker_taskrun
uv run python -m worker.worker_indexjob

cd frontend
npm install
npm run dev
```

