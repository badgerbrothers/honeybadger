# Feature: Auth Service + User-Owned Projects/Conversations

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the correct files and preserve current service boundaries.

## Feature Description

Introduce a dedicated `auth-service` and enforce per-user data isolation so each authenticated user can only access their own projects and conversations (and downstream task/run/artifact/rag data tied to those projects).

This includes:
- New authentication domain (`register/login/refresh/logout/me`)
- JWT-based identity propagation
- Ownership model (`projects.owner_user_id`) as the tenant boundary
- Authorization enforcement across `project-service`, `task-service`, and `rag-service`
- Internal worker-to-task-service calls secured without breaking queue execution

## User Story

As an authenticated user  
I want to access only my own projects and conversations  
So that my data is isolated from other users in the same deployment

## Problem Statement

Current system is effectively single-user:
- No auth middleware in microservices
- No user model or token issuance
- Resource endpoints query by IDs without ownership checks
- API gateway has no `/api/auth` route

Result: in multi-user scenarios, any caller can read/modify resources by UUID if discovered.

## Solution Statement

Implement a dedicated `auth-service` that issues JWT access/refresh tokens and stores user credentials + refresh session records. Add `owner_user_id` to `projects` and enforce authorization via:
- Token verification dependency in each user-facing service
- Query filtering by ownership through `projects.owner_user_id`
- Internal service token for worker callbacks and event ingestion endpoints

This keeps current microservice split intact and adds least-disruptive multi-user isolation.

## Feature Metadata

**Feature Type**: New Capability  
**Estimated Complexity**: High  
**Primary Systems Affected**: `services/auth-service`, `project-service`, `task-service`, `rag-service`, `nginx`, `docker-compose`, `frontend`, DB migration path  
**Dependencies**: FastAPI security dependencies, JWT library, password hashing library, Alembic migration workflow, existing shared Postgres schema

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `services/project-service/app/routers/projects.py` (lines 22-176) - Existing CRUD/file upload pattern; no auth filtering yet.
- `services/project-service/app/routers/conversations.py` (lines 12-74) - Conversation endpoints currently unguarded.
- `services/project-service/app/models/project.py` (lines 13-24) - `Project` model currently has no ownership field.
- `services/project-service/app/main.py` (lines 27-36) - Router registration pattern for service entrypoint.
- `services/project-service/app/config.py` (lines 6-61) - Settings pattern for env-based config.

- `services/task-service/app/routers/tasks.py` (lines 57-241) - Task lifecycle APIs; needs ownership enforcement.
- `services/task-service/app/routers/runs.py` (lines 17-83) - Run retrieval/events/websocket endpoints.
- `services/task-service/app/routers/artifacts.py` (full file) - Artifact access paths include worker upload route.
- `services/task-service/app/models/project.py` (lines 13-24) - Local service view of `projects` table; must stay schema-compatible.
- `services/task-service/app/main.py` (lines 30-40) - Middleware/router mounting pattern.

- `services/rag-service/app/routers/rag.py` (lines 23-86) - Project-scoped index/search/chunks endpoints.
- `services/rag-service/app/services/rag_service.py` (full file) - Search/index orchestration keyed by `project_id`.
- `services/rag-service/app/main.py` (lines 27-35) - Service route registration.

- `worker/services/backend_client.py` (lines 16-44) - Worker emits run events and uploads artifacts via task-service HTTP APIs.
- `worker/worker_taskrun.py` (lines 24-33) - Worker consumes queue and executes run; auth changes must not break this path.

- `nginx/nginx.conf` (lines 33-79) - Existing gateway route map; add `/api/auth`.
- `docker-compose.yml` (lines 59-295) - Service env wiring and ports; add auth-service + JWT/shared secrets.
- `.env.example` (lines 1-49) - Central env sample; add auth/JWT/internal token vars.

- `backend/alembic/env.py` (lines 13-23, 35-56) - Existing Alembic wiring still used in repo.
- `backend/alembic/versions/006_task_queue_fields.py` (lines 18-53) - Current migration style for additive schema updates.
- `backend/alembic/versions/1004c8374fe5_initial_schema_with_all_models.py` (lines 19-35) - Baseline table history; confirms no auth tables yet.

- `services/task-service/tests/test_models_api.py` (lines 42-58, 72-113) - Service-level API test style using FastAPI + dependency override.
- `backend/tests/conftest.py` (lines 17-45, 67-74) - Existing async test scaffolding conventions.

- `.claude/PRD.md` (lines 673-680, 775) - Product explicitly marks auth as future requirement (now being implemented).
- `.claude/reference/fastapi-best-practices.md` (lines 313-327, 718-749) - Dependency chaining and security baseline patterns.

### New Files to Create

- `services/auth-service/Dockerfile`
- `services/auth-service/pyproject.toml`
- `services/auth-service/app/__init__.py`
- `services/auth-service/app/main.py`
- `services/auth-service/app/config.py`
- `services/auth-service/app/database.py`
- `services/auth-service/app/models/base.py`
- `services/auth-service/app/models/user.py`
- `services/auth-service/app/models/refresh_token.py`
- `services/auth-service/app/models/__init__.py`
- `services/auth-service/app/schemas/auth.py`
- `services/auth-service/app/schemas/user.py`
- `services/auth-service/app/schemas/__init__.py`
- `services/auth-service/app/security/passwords.py`
- `services/auth-service/app/security/tokens.py`
- `services/auth-service/app/security/dependencies.py`
- `services/auth-service/app/routers/auth.py`
- `services/auth-service/app/routers/users.py`
- `services/auth-service/app/routers/__init__.py`
- `services/auth-service/tests/test_auth_api.py`
- `services/auth-service/tests/test_tokens.py`
- `services/auth-service/tests/test_passwords.py`

- `services/project-service/app/security/auth.py`
- `services/task-service/app/security/auth.py`
- `services/rag-service/app/security/auth.py`

- `backend/alembic/versions/<new_revision>_auth_users_and_project_owner.py`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI: OAuth2 with Password + JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
  - Specific sections: install PyJWT, password hashing, dependency updates
  - Why: canonical FastAPI pattern for token auth dependencies and `/token` flow

- [PyJWT Usage](https://pyjwt.readthedocs.io/en/stable/usage.html)
  - Specific sections: expiration (`exp`), decode validation, algorithms
  - Why: token issue/verify implementation details used by auth-service and verifier dependencies

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
  - Specific sections: Argon2id recommendations and work factor guidance
  - Why: secure password hashing defaults and migration-safe policy

- [SQLAlchemy AsyncIO ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - Specific sections: `AsyncSession`, execution patterns
  - Why: maintain consistent async DB access across new auth-service

- [Alembic Operation Reference](https://alembic.sqlalchemy.org/en/latest/ops.html)
  - Specific sections: `add_column`, `create_table`, indexes, constraints
  - Why: required for additive migration of `users`, `refresh_tokens`, and `projects.owner_user_id`

- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
  - Specific sections: env mapping and settings models
  - Why: align new config with existing `SettingsConfigDict(env_file=".env", extra="ignore")` pattern

### Patterns to Follow

**Router and DB dependency pattern**
```python
# services/project-service/app/routers/projects.py (lines 22-30)
@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    return result.scalars().all()
```

**Config pattern**
```python
# services/task-service/app/config.py (lines 6-10)
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**Service startup pattern**
```python
# services/task-service/app/main.py (lines 13-20)
@app.on_event("startup")
async def startup_event():
    import app.models  # noqa: F401
    await init_db()
```

**Error handling/logging pattern**
```python
# services/task-service/app/routers/tasks.py (lines 165-183)
try:
    await queue_service.publish_task_run(publish_run_id)
except Exception as exc:
    logger.error("task_queue_status_publish_failed", ...)
    raise HTTPException(status_code=503, detail="Task run queue unavailable")
```

**Async API testing pattern**
```python
# services/task-service/tests/test_models_api.py (lines 72-79)
@pytest.mark.asyncio
async def test_create_task_with_explicit_supported_model(test_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/api/tasks/", json=payload)
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Auth Domain)

Create `auth-service` as an isolated microservice with user identity and token lifecycle.

**Tasks:**
- Scaffold service structure mirroring existing service layout
- Implement user and refresh token models
- Implement password hashing + JWT issue/verify
- Expose auth endpoints and `/api/users/me`

### Phase 2: Data Ownership Model

Introduce ownership boundary in core data model.

**Tasks:**
- Add `projects.owner_user_id` with FK to users table
- Backfill legacy projects with a deterministic seed/system user
- Add required indexes and enforce non-null after backfill
- Keep migration idempotent and rollback-safe

### Phase 3: Service Authorization Integration

Enforce authenticated access and owner filtering in existing services.

**Tasks:**
- Add auth dependency module to project/task/rag services
- Require current user for user-facing endpoints
- Filter queries by ownership and reject cross-user access
- Preserve internal worker callbacks via internal service token path

### Phase 4: Gateway + Runtime Wiring

Integrate auth-service into deployment and routing.

**Tasks:**
- Add `auth-service` to compose
- Add `/api/auth` and `/api/users` gateway routes
- Add shared JWT/internal token env variables
- Update frontend API/session handling

### Phase 5: Testing & Validation

Add unit/integration tests and e2e verification commands for auth + data isolation.

**Tasks:**
- Auth-service unit and API tests
- Ownership enforcement tests across project/task/rag services
- Internal worker callback auth tests
- Manual multi-user verification walkthrough

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE services/auth-service service skeleton

- **IMPLEMENT**: Create service folder structure and baseline files (`main/config/database/models/schemas/routers/security/tests`).
- **PATTERN**: Mirror `services/project-service` structure and Dockerfile conventions.
- **IMPORTS**: FastAPI, SQLAlchemy async, Pydantic settings, structlog.
- **GOTCHA**: Keep `WORKDIR /app`, `uv sync`, and `uvicorn app.main:app` startup parity with existing services.
- **VALIDATE**: `cd services/auth-service && uv sync`

### CREATE auth data models and schemas

- **IMPLEMENT**: `User` and `RefreshTokenSession` models with UUID PKs, timestamps, uniqueness on `email`, and token/session metadata.
- **PATTERN**: Timestamp mixin style from `services/*/app/models/base.py`.
- **IMPORTS**: `sqlalchemy.orm.Mapped`, `mapped_column`, `relationship`, `uuid`, `datetime`.
- **GOTCHA**: Store refresh token hash, not raw token; track revoked/rotated state.
- **VALIDATE**: `cd services/auth-service && uv run python -c "import app.models; print('models-ok')"`

### CREATE password and token security modules

- **IMPLEMENT**:
  - password hash/verify helpers (Argon2id)
  - access/refresh token creators
  - decode/validate helper for shared claim parsing
- **PATTERN**: Dependency chaining pattern from `.claude/reference/fastapi-best-practices.md:316-327`.
- **IMPORTS**: `jwt`, datetime utilities, hash library.
- **GOTCHA**: Enforce `exp`, token type (`access` vs `refresh`), issuer/audience consistency.
- **VALIDATE**: `cd services/auth-service && uv run pytest tests/test_tokens.py -v`

### CREATE auth routers (`/api/auth`, `/api/users/me`)

- **IMPLEMENT**:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/refresh`
  - `POST /api/auth/logout`
  - `GET /api/users/me`
- **PATTERN**: Router composition from `services/project-service/app/main.py:35-36`.
- **IMPORTS**: FastAPI `Depends`, `HTTPException`, DB session dependency, security dependencies.
- **GOTCHA**: Refresh rotation should invalidate prior session record on each refresh.
- **VALIDATE**: `cd services/auth-service && uv run pytest tests/test_auth_api.py -v`

### UPDATE docker-compose and gateway for auth-service

- **IMPLEMENT**:
  - Add `auth-service` container to `docker-compose.yml`
  - Add `api-gateway` dependency on `auth-service`
  - Add auth route entries in `nginx/nginx.conf` for `/api/auth` and `/api/users`
- **PATTERN**: Existing route mapping style in `nginx/nginx.conf:33-79`.
- **IMPORTS**: N/A
- **GOTCHA**: Route prefixes are currently non-trailing-slash locations; preserve behavior consistency.
- **VALIDATE**: `docker compose config`

### UPDATE env contract for JWT and internal service auth

- **IMPLEMENT**:
  - Add to `.env.example`: `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ACCESS_EXPIRE_MINUTES`, `JWT_REFRESH_EXPIRE_DAYS`, `JWT_ISSUER`, `JWT_AUDIENCE`, `INTERNAL_SERVICE_TOKEN`
  - Add corresponding settings fields to `auth-service` and verifier services
- **PATTERN**: Settings style in `services/project-service/app/config.py:6-61`.
- **IMPORTS**: `Field`, `AliasChoices` as needed.
- **GOTCHA**: Ensure consistent secret/issuer/audience across all verifier services.
- **VALIDATE**: `rg -n "JWT_|INTERNAL_SERVICE_TOKEN" .env.example services/auth-service/app/config.py services/project-service/app/config.py services/task-service/app/config.py services/rag-service/app/config.py`

### CREATE migration for users + project ownership

- **IMPLEMENT**: New Alembic revision in `backend/alembic/versions/` that:
  - creates `users` table
  - creates `refresh_token_sessions` (or equivalent) table
  - adds `projects.owner_user_id` FK -> `users.id`
  - backfills existing projects to seed/system user
  - adds indexes (`users.email`, `projects.owner_user_id`, token session lookup indexes)
  - sets `projects.owner_user_id` non-null after backfill
- **PATTERN**: additive migration style from `backend/alembic/versions/006_task_queue_fields.py:18-53`.
- **IMPORTS**: `alembic.op`, `sqlalchemy as sa`.
- **GOTCHA**: `create_all` in service startup does not alter existing tables (`services/project-service/app/database.py:40-41`), so migration is mandatory.
- **VALIDATE**: `cd backend && uv run alembic upgrade head`

### UPDATE project-service models/schemas and enforce ownership

- **IMPLEMENT**:
  - Add `owner_user_id` to `Project` model
  - Optionally expose ownership in response schema only if needed by frontend
  - Add auth dependency and filter all project/conversation queries by current user
  - On create project, set `owner_user_id = current_user.id`
  - On create conversation, verify project belongs to current user
- **PATTERN**: Query+guard style in `services/project-service/app/routers/projects.py:36-63`.
- **IMPORTS**: `Depends(get_current_user)`, SQLAlchemy joins/filters.
- **GOTCHA**: Return `404` for foreign resources to reduce IDOR signal.
- **VALIDATE**: `cd services/project-service && uv run pytest -q`

### UPDATE task-service authorization and ownership checks

- **IMPLEMENT**:
  - Add auth dependency for user-facing task/run/artifact endpoints
  - Join/filter via `Project.owner_user_id` for all reads/writes
  - Validate `task.project_id` ownership during create/update transitions
  - Protect run retrieval and artifact listing by owner scope
- **PATTERN**: Existing endpoint flow in `services/task-service/app/routers/tasks.py:57-241`, `runs.py:17-72`.
- **IMPORTS**: `Project` model joins + auth dependency.
- **GOTCHA**: `POST /api/tasks/{id}/runs` and queue status transitions must fail authorization before enqueue.
- **VALIDATE**: `cd services/task-service && uv run pytest tests/test_models_api.py -v`

### UPDATE rag-service authorization for project-scoped routes

- **IMPLEMENT**:
  - Require auth on `/api/rag/projects/*`
  - Validate `project_id` belongs to current user before index/search/chunk operations
- **PATTERN**: Existing route handlers in `services/rag-service/app/routers/rag.py:23-86`.
- **IMPORTS**: auth dependency + `Project` ownership query.
- **GOTCHA**: Keep existing queue/index behavior unchanged after ownership check.
- **VALIDATE**: `cd services/rag-service && uv run pytest -q`

### ADD internal service authentication path for worker callbacks

- **IMPLEMENT**:
  - Introduce `X-Internal-Service-Token` validation dependency for internal-only routes:
    - `/api/runs/{run_id}/events`
    - worker artifact upload path (`/api/artifacts/upload`) if invoked by worker
  - Update worker `BackendClient` to send internal token header
- **PATTERN**: Worker client call points in `worker/services/backend_client.py:16-44`.
- **IMPORTS**: `httpx` header injection in worker client, service config secret in task-service.
- **GOTCHA**: Do not break local queue worker flow in compose (`worker-taskrun` uses direct `task-service` URL).
- **VALIDATE**: `cd worker && uv run pytest tests/test_main.py tests/test_agent.py -v`

### UPDATE frontend login/session wiring

- **IMPLEMENT**:
  - Replace placeholder login action with real `POST /api/auth/login`
  - Store access token for API calls (prefer in-memory + refresh flow; if localStorage used, keep short TTL)
  - Add refresh handling and logout path
  - Attach `Authorization: Bearer` in API helper for protected routes
- **PATTERN**: Existing `app/login/page.tsx` route and workspace navigation flow.
- **IMPORTS**: lightweight API utility + auth context/store.
- **GOTCHA**: Current frontend is mid-refactor; keep auth integration modular and avoid coupling to transient prototype pages.
- **VALIDATE**: `cd frontend && npm run build`

### CREATE authorization-focused tests

- **IMPLEMENT**:
  - `auth-service` unit + API tests
  - project/task/rag service tests for cross-user isolation
  - tests for internal-token-only endpoints
- **PATTERN**: Async test style from `services/task-service/tests/test_models_api.py:72-113`.
- **IMPORTS**: `pytest`, `httpx.AsyncClient`, dependency overrides/mocks.
- **GOTCHA**: Include both positive (`owner`) and negative (`non-owner`) cases.
- **VALIDATE**: `uv run pytest services/auth-service/tests services/task-service/tests -v`

### UPDATE docs/runbook

- **IMPLEMENT**:
  - README microservice section: add auth-service startup and envs
  - Document protected endpoints and token flow
  - Add migration run command before compose startup for upgraded environments
- **PATTERN**: Current operational docs style in `README.md`.
- **IMPORTS**: N/A
- **GOTCHA**: Explicitly note backward-incompatible requirement for owner backfill migration.
- **VALIDATE**: `rg -n "auth-service|JWT_|/api/auth|owner_user_id" README.md docs`

---

## TESTING STRATEGY

### Unit Tests

Scope:
- Password hashing/verification (happy + invalid input)
- JWT issue/verify (`exp`, `aud`, `iss`, token type)
- Refresh token rotation and revocation behavior

Requirements:
- Deterministic token tests using frozen time where practical
- No plaintext token persistence assertions

### Integration Tests

Scope:
- Register/login/refresh/logout/me end-to-end
- User A cannot access User B projects/conversations/tasks/runs/artifacts/rag chunks
- Worker internal callback endpoints accept only valid internal service token

Requirements:
- Two-user fixture setup
- Resource ownership assertions for list + detail + mutation endpoints

### Edge Cases

- Duplicate email registration (409 or 400 with explicit reason)
- Expired access token (401)
- Expired/revoked refresh token (401)
- Refresh token replay after rotation (401)
- Cross-user UUID access attempts return 404 (or policy-consistent 403)
- Missing internal token on worker endpoints rejected
- Migration re-run safety in non-empty DB

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and feature correctness.

### Level 1: Syntax & Static Checks

```bash
cd services/auth-service && uv run python -m compileall app
cd services/project-service && uv run python -m compileall app
cd services/task-service && uv run python -m compileall app
cd services/rag-service && uv run python -m compileall app
cd worker && uv run python -m compileall .
```

### Level 2: Targeted Unit/Service Tests

```bash
cd services/auth-service && uv run pytest tests/test_passwords.py tests/test_tokens.py -v
cd services/auth-service && uv run pytest tests/test_auth_api.py -v
cd services/task-service && uv run pytest tests/test_models_api.py -v
```

### Level 3: Cross-Service API Validation

```bash
docker compose up --build -d
curl -s http://localhost/health
curl -s http://localhost/api/auth/health
```

### Level 4: Manual Validation (Multi-User Isolation)

```bash
# 1) Register two users
# 2) Login each user and capture access tokens
# 3) User A creates project + conversation
# 4) User B attempts to read User A resources (must fail by policy)
# 5) User A can still read/write own resources
# 6) Create task/run and verify worker event ingestion still works
```

### Level 5: Migration Validation

```bash
cd backend && uv run alembic current
cd backend && uv run alembic upgrade head
cd backend && uv run alembic downgrade -1
cd backend && uv run alembic upgrade head
```

---

## ACCEPTANCE CRITERIA

- [ ] `auth-service` exists and exposes register/login/refresh/logout/me APIs
- [ ] JWT access/refresh lifecycle is implemented with secure validation
- [ ] Passwords are hashed using Argon2id-compatible settings
- [ ] `projects` table includes `owner_user_id` with FK and index
- [ ] Existing project rows are backfilled during migration
- [ ] `project-service` only returns/modifies owner resources
- [ ] `task-service` enforces ownership for task/run/artifact operations
- [ ] `rag-service` enforces ownership for project-scoped rag operations
- [ ] Worker internal callback paths continue to function with service token auth
- [ ] Gateway routes include `/api/auth` and `/api/users`
- [ ] Frontend login flow uses real auth API and sends bearer token
- [ ] All listed validation commands execute successfully
- [ ] No regressions in task queue execution path

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Migration tested on non-empty DB
- [ ] Auth and ownership tests pass
- [ ] Worker callback integration verified
- [ ] Gateway route updates validated
- [ ] Frontend auth flow validated manually
- [ ] Documentation updated
- [ ] Security review completed for token/session handling

---

## NOTES

### Key Design Decisions

- **Ownership root at `projects.owner_user_id`**: keeps tenancy model simple and aligns with current resource graph (`conversation/task/artifact` already references `project_id`).
- **Dedicated auth-service**: clean separation of authentication domain from business domains.
- **Local token verification in each service**: avoids auth-service hot path on every request; better resilience and latency.
- **Internal service token for worker callbacks**: protects machine-to-machine endpoints without forcing worker into user-session semantics.

### Risks and Mitigations

- **Risk**: `create_all` masks missing migrations in dev.
  - **Mitigation**: enforce Alembic migration as required deployment step.
- **Risk**: legacy `backend/` path diverges from `services/`.
  - **Mitigation**: keep migration canonical under existing Alembic folder and document supported runtime path.
- **Risk**: frontend mid-refactor could cause auth UX churn.
  - **Mitigation**: isolate token handling in a small API/auth module and avoid deep coupling to prototype routes.

### Out of Scope (for this feature)

- Organization/team sharing model (`project_members`)
- Fine-grained RBAC/ABAC beyond owner checks
- SSO/SAML/OIDC third-party identity providers
- Rate limiting and abuse controls (recommended follow-up)

### Confidence Score

**8.5 / 10** for one-pass implementation success, assuming migration execution discipline and explicit handling of worker internal endpoints.

