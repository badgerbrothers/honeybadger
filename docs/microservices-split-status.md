# Microservices Split Status

This file tracks the implementation status of `.agents/plans/microservices-split-architecture.md`.

## Completed

- Created `services/` domain folders for:
  - `project-service`
  - `task-service`
  - `rag-service`
  - `storage-service`
- Added service-level `pyproject.toml` and `Dockerfile` for project/task/rag/storage.
- Added service entrypoints:
  - `services/project-service/app/main.py`
  - `services/task-service/app/main.py`
  - `services/rag-service/app/main.py`
  - `services/storage-service/app/main.py`
- Routed APIs through API Gateway in `nginx/nginx.conf`:
  - `/api/projects`, `/api/conversations` -> project-service
  - `/api/tasks`, `/api/runs`, `/api/artifacts` -> task-service
  - `/api/rag` -> rag-service
  - `/api/storage` -> storage-service
- Updated `docker-compose.yml` to orchestrate split services and gateway.
- Updated frontend defaults to target gateway base URLs.
- Project/task services now proxy storage operations via HTTP to storage-service.
- Project-service now calls rag-service HTTP API to schedule indexing.
- Added `.dockerignore` files to reduce build context size and improve build stability.
- Docker validation completed (`docker compose ps` healthy for gateway + 4 services + workers).
- Gateway routing checks completed:
  - `GET /api/projects` -> `307`
  - `GET /api/tasks` -> `307`
  - `GET /api/rag` -> `200`
  - `GET /api/storage` -> `200`
- End-to-end API flow completed through gateway:
  - created project and uploaded file
  - created conversation and task
  - created run and observed worker consumption + event ingestion
  - confirmed sandbox container creation in worker logs (no longer blocked by missing image)
  - run terminal state reached (`failed`) due upstream model provider request blocked, not service wiring
- Artifact API flow completed:
  - upload artifact
  - download artifact
  - save artifact to project (storage copy path verified)
- Index worker flow observed:
  - document indexing job consumed and completed for uploaded file

## Partial / Transitional

- Worker code remains in root `worker/` package, while service worker entry files exist under:
  - `services/task-service/worker/taskrun_worker.py`
  - `services/rag-service/worker/indexjob_worker.py`
- Database is still shared (`badgers`) for now; this follows the plan note recommending shared DB first.
- Legacy `backend/` package models are still imported by worker runtime paths.

## Deferred (Not executed in this cycle)

- Per-service isolated databases and full cross-service HTTP client decoupling are not finalized.
- Legacy `backend/` directory was not removed yet to avoid breaking existing local workflows before final verification.

## Next Actions

1. Remove/retire legacy `backend` runtime imports from worker and service packages.
2. Decide migration strategy for shared DB -> per-service DBs (compose + schema management).
3. Add explicit websocket stream verification script to automated E2E checks.
