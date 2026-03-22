# Feature: Auth Service (Java) + User Resource Isolation

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a dedicated Java `auth-service` and enforce strict per-user ownership for project-centric resources across the current microservices system.

Primary business outcome:
- Each user only sees and mutates their own `project` and `conversation` (and downstream `task/run/artifact/rag` data linked to those projects).
- Current worker execution chain continues to work without requiring end-user tokens.

## User Story

As a logged-in user  
I want my own projects and conversations to be isolated  
So that no other user can access or modify my data

## Problem Statement

The current stack is effectively single-user:
- No authentication middleware in `project-service`, `task-service`, `rag-service`.
- No user table / login / token issuance.
- Resource routes rely on UUID lookup only.
- Gateway has no auth route split.

This creates immediate multi-user security risk (IDOR-style access if UUIDs are known).

## Solution Statement

Add a new Java `auth-service` (Spring Boot) to issue and refresh JWTs, then enforce ownership in existing Python services with local JWT verification and project-based scoping.

Authorization model:
- Source of truth: `projects.owner_user_id`.
- Any access to conversation/task/run/artifact/rag must be validated through owning project.
- Worker internal callbacks use a separate internal service token and do not depend on user bearer tokens.

## Feature Metadata

**Feature Type**: New Capability  
**Estimated Complexity**: High  
**Primary Systems Affected**: `services/auth-service`, `project-service`, `task-service`, `rag-service`, `nginx`, `docker-compose.yml`, `frontend`, DB migrations  
**Dependencies**: Spring Boot Security/JWT, existing FastAPI dependency system, Postgres schema migration tooling

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `services/project-service/app/routers/projects.py` (lines 22-176) - Current project CRUD and file flows; no owner filter.
- `services/project-service/app/routers/conversations.py` (lines 12-74) - Conversation APIs currently lack auth checks.
- `services/project-service/app/models/project.py` (lines 13-24) - `Project` model currently has no `owner_user_id`.
- `services/project-service/app/schemas/project.py` (lines 17-26) - Response schema may need owner metadata decision.
- `services/project-service/app/config.py` (lines 6-61) - Service-level settings pattern.
- `services/project-service/app/main.py` (lines 27-41) - Middleware/router registration pattern.

- `services/task-service/app/routers/tasks.py` (lines 57-241) - Task creation/list/run creation flows must be ownership-scoped.
- `services/task-service/app/routers/runs.py` (lines 17-83) - Run detail/stream/events endpoints; mixed user vs internal calls.
- `services/task-service/app/routers/artifacts.py` (full file) - Artifact upload/download/list endpoints need scoped access rules.
- `services/task-service/app/models/project.py` (lines 13-24) - Local view of shared `projects` table; must stay schema aligned.
- `services/task-service/app/config.py` (lines 6-85) - Add JWT/internal token settings.

- `services/rag-service/app/routers/rag.py` (lines 23-86) - Project-scoped index/search/chunk APIs require owner guard.
- `services/rag-service/app/services/rag_service.py` (full file) - Project ID driven operations that assume trusted callers.
- `services/rag-service/app/config.py` (lines 6-59) - Add JWT validation settings.

- `worker/services/backend_client.py` (lines 16-44) - Worker emits run events/uploads artifacts to task-service.
- `worker/worker_taskrun.py` (lines 24-33) - Queue consumer path that must not break after auth enforcement.

- `nginx/nginx.conf` (lines 33-79) - Existing route splits; add auth upstream/path routing.
- `docker-compose.yml` (lines 59-295) - Add auth-service container and shared env wiring.
- `.env.example` (lines 1-49) - Add JWT/internal token config contract.

- `backend/alembic/versions/1004c8374fe5_initial_schema_with_all_models.py` (lines 19-35) - Baseline schema confirms no user/auth tables.
- `backend/alembic/versions/006_task_queue_fields.py` (lines 18-53) - Migration style for additive schema evolution.
- `backend/alembic/env.py` (lines 13-23, 35-56) - Existing Alembic environment wiring.

- `.claude/prd_auth.md` (full file) - Product requirement baseline for this feature.
- `.claude/PRD.md` (lines 673-680, 775) - Historical statement: auth was deferred and now becomes in-scope.
- `.claude/reference/fastapi-best-practices.md` (lines 316-327, 718-749) - Dependency and security patterns to mirror.

### New Files to Create

- `services/auth-service/pom.xml`
- `services/auth-service/Dockerfile`
- `services/auth-service/src/main/java/.../AuthServiceApplication.java`
- `services/auth-service/src/main/java/.../config/SecurityConfig.java`
- `services/auth-service/src/main/java/.../config/JwtProperties.java`
- `services/auth-service/src/main/java/.../domain/User.java`
- `services/auth-service/src/main/java/.../domain/RefreshTokenSession.java`
- `services/auth-service/src/main/java/.../repository/UserRepository.java`
- `services/auth-service/src/main/java/.../repository/RefreshTokenSessionRepository.java`
- `services/auth-service/src/main/java/.../service/AuthService.java`
- `services/auth-service/src/main/java/.../service/JwtService.java`
- `services/auth-service/src/main/java/.../controller/AuthController.java`
- `services/auth-service/src/main/java/.../controller/UserController.java`
- `services/auth-service/src/main/resources/application.yml`
- `services/auth-service/src/main/resources/db/migration/V1__create_auth_tables.sql`
- `services/auth-service/src/test/java/.../AuthControllerTest.java`

- `services/project-service/app/security/auth.py`
- `services/task-service/app/security/auth.py`
- `services/rag-service/app/security/auth.py`

- `backend/alembic/versions/<new_rev>_add_owner_user_id_and_user_tables.py`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Spring Security Reference](https://docs.spring.io/spring-security/reference/index.html)
  - Specific section: stateless authentication and filter chain.
  - Why: define secure JWT auth in Java service.

- [Spring Boot Reference](https://docs.spring.io/spring-boot/docs/current/reference/htmlsingle/)
  - Specific section: externalized configuration and Actuator health.
  - Why: align runtime config and health checks with current compose setup.

- [JJWT Documentation](https://github.com/jwtk/jjwt)
  - Specific section: signing/verification and expiration claims.
  - Why: robust JWT handling in auth-service.

- [FastAPI OAuth2/JWT Tutorial](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
  - Specific section: dependency-based current-user extraction.
  - Why: Python services need local JWT verification dependency pattern.

- [SQLAlchemy AsyncIO ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - Specific section: async session query patterns.
  - Why: enforce owner filters using current async DB access style.

- [Alembic Operation Reference](https://alembic.sqlalchemy.org/en/latest/ops.html)
  - Specific section: `create_table`, `add_column`, `create_index`, constraint operations.
  - Why: additive migration path for `owner_user_id` and auth tables.

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
  - Specific section: Argon2id recommendations.
  - Why: password hashing policy in auth-service.

### Patterns to Follow

**FastAPI route + DB dependency pattern**
```python
# services/project-service/app/routers/projects.py
@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    return result.scalars().all()
```

**Settings pattern**
```python
# services/project-service/app/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**Error handling/logging style**
```python
# services/task-service/app/routers/tasks.py
except Exception as exc:
    logger.error("task_run_publish_failed", error=str(exc), exc_info=True)
    raise HTTPException(status_code=503, detail="Task run queue unavailable")
```

**Async API tests pattern**
```python
# services/task-service/tests/test_models_api.py
async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
    response = await client.post("/api/tasks/", json=payload)
```

---

## IMPLEMENTATION PLAN

### Phase 1: Auth Service Foundation

Build the Java auth-service with secure token lifecycle and health endpoint.

**Tasks:**
- Create Spring Boot project skeleton and dependency graph.
- Implement user + refresh token persistence.
- Implement register/login/refresh/logout/me API contracts.
- Add Flyway migration and integration tests.

### Phase 2: Data Ownership Foundation

Introduce ownership column in core project model and migrate existing data.

**Tasks:**
- Add `projects.owner_user_id` with FK/index.
- Create users/auth tables in migration path used by current deployment.
- Backfill legacy projects to deterministic seed/system user.
- Enforce non-null on owner column after backfill.

### Phase 3: Authorization in Python Services

Integrate JWT verification dependency and ownership guards.

**Tasks:**
- Add shared auth dependency module to project/task/rag services.
- Scope all user-facing resource queries by ownership.
- Differentiate internal machine endpoints from user endpoints.

### Phase 4: Gateway, Worker, Frontend Integration

Wire complete system runtime behavior.

**Tasks:**
- Add auth routes/upstream in nginx.
- Add auth-service and shared secrets to compose/env.
- Pass internal service token in worker backend client headers.
- Connect frontend login and bearer token request flow.

### Phase 5: Validation & Hardening

Close functional/security/testing gaps and verify no regressions.

**Tasks:**
- Add multi-user isolation tests.
- Validate queue-worker end-to-end flow.
- Verify refresh rotation, revocation, and expiry behavior.
- Update docs and operational runbook.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE `services/auth-service` Java service scaffold

- **IMPLEMENT**: Initialize Maven Spring Boot project with `web`, `security`, `validation`, `data-jpa`, `actuator`, `flyway`, `postgresql`, and test dependencies.
- **PATTERN**: Mirror service container conventions from `services/project-service/Dockerfile:1-10`.
- **IMPORTS**: Spring Boot starters + JJWT (or Nimbus) + Testcontainers.
- **GOTCHA**: Keep health endpoint path compatible with compose checks.
- **VALIDATE**: `cd services/auth-service && mvn -q -DskipTests package`

### CREATE auth domain models and repositories

- **IMPLEMENT**: `User` and `RefreshTokenSession` entities; unique email; hashed refresh token session storage.
- **PATTERN**: UUID/timestamp structure similar to existing SQL tables in `backend/alembic/versions/1004c8374fe5_initial_schema_with_all_models.py`.
- **IMPORTS**: JPA annotations, UUID, Instant.
- **GOTCHA**: Never persist raw password or raw refresh token.
- **VALIDATE**: `cd services/auth-service && mvn -q test -Dtest=*Repository*`

### CREATE JWT + password security layer in auth-service

- **IMPLEMENT**: Password hash/verify service, access/refresh token creation, token parsing and validation.
- **PATTERN**: Claim validation constraints from `.claude/prd_auth.md` security section.
- **IMPORTS**: `io.jsonwebtoken.*` (or Nimbus API), secure password encoder.
- **GOTCHA**: Enforce `iss`, `aud`, `exp`, and token type claim.
- **VALIDATE**: `cd services/auth-service && mvn -q test -Dtest=*Jwt*`

### CREATE auth-service controllers and API contracts

- **IMPLEMENT**:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/refresh`
  - `POST /api/auth/logout`
  - `GET /api/users/me`
- **PATTERN**: Existing service style returns simple JSON and uses health endpoint.
- **IMPORTS**: DTOs + validation annotations.
- **GOTCHA**: Refresh rotation should invalidate prior session and mint a new refresh token.
- **VALIDATE**: `cd services/auth-service && mvn -q test -Dtest=*AuthController*`

### UPDATE `docker-compose.yml` to include auth-service

- **IMPLEMENT**: Add `auth-service` build, env, healthcheck, and gateway dependency links.
- **PATTERN**: Service blocks under `docker-compose.yml:59-295`.
- **IMPORTS**: N/A
- **GOTCHA**: Avoid port conflicts; keep internal network names consistent.
- **VALIDATE**: `docker compose config`

### UPDATE `nginx/nginx.conf` to route auth APIs

- **IMPLEMENT**: Add `upstream auth_service` and location routes for `/api/auth` and `/api/users`.
- **PATTERN**: Existing route mapping style `nginx/nginx.conf:33-79`.
- **IMPORTS**: N/A
- **GOTCHA**: Preserve websocket config for `/api/runs`.
- **VALIDATE**: `docker run --rm -v "${PWD}/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" nginx:latest nginx -t`

### UPDATE env and config contracts across services

- **IMPLEMENT**: Add JWT/internal token variables in `.env.example` and settings classes:
  - `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_ISSUER`, `JWT_AUDIENCE`
  - `JWT_ACCESS_EXPIRE_MINUTES`, `JWT_REFRESH_EXPIRE_DAYS`
  - `INTERNAL_SERVICE_TOKEN`, `AUTH_SERVICE_URL`
- **PATTERN**: Settings models in `services/*/app/config.py`.
- **IMPORTS**: `Field`, `AliasChoices` where needed.
- **GOTCHA**: Same signing+validation parameters must be used consistently across auth/project/task/rag services.
- **VALIDATE**: `rg -n "JWT_|AUTH_SERVICE_URL|INTERNAL_SERVICE_TOKEN" .env.example services`

### CREATE migration for users/auth tables + owner column

- **IMPLEMENT**: New migration to create `users`, `refresh_token_sessions`, and add `projects.owner_user_id` with index/FK/backfill/non-null.
- **PATTERN**: Additive migration style in `backend/alembic/versions/006_task_queue_fields.py:18-53`.
- **IMPORTS**: `alembic.op`, `sqlalchemy as sa`.
- **GOTCHA**: Current service startup `create_all` does not evolve existing schemas (`services/project-service/app/database.py:40-41`).
- **VALIDATE**: `cd backend && uv run alembic upgrade head`

### UPDATE project-service for authenticated ownership filtering

- **IMPLEMENT**: Add auth dependency module and enforce owner scoping in project/conversation endpoints.
- **PATTERN**: Query-first then `HTTPException(404)` pattern from `services/project-service/app/routers/projects.py:36-63`.
- **IMPORTS**: auth dependency, current user schema, ownership helper queries.
- **GOTCHA**: Cross-user resources should not leak existence.
- **VALIDATE**: `cd services/project-service && uv run pytest -q`

### UPDATE task-service for ownership + internal endpoint split

- **IMPLEMENT**:
  - protect user-facing task/run/artifact routes with bearer auth + ownership checks
  - protect worker callback routes with `X-Internal-Service-Token`
- **PATTERN**: Route groups in `services/task-service/app/routers/tasks.py` and `runs.py`.
- **IMPORTS**: auth dependencies, ownership join checks.
- **GOTCHA**: keep worker flow intact for `/api/runs/{run_id}/events` and artifact upload.
- **VALIDATE**: `cd services/task-service && uv run pytest tests/test_models_api.py -v`

### UPDATE rag-service for ownership guard

- **IMPLEMENT**: enforce current-user ownership check for `index/search/list/delete chunk` endpoints.
- **PATTERN**: `services/rag-service/app/routers/rag.py:23-86`.
- **IMPORTS**: auth dependency + project ownership lookup.
- **GOTCHA**: do ownership check before expensive retrieval work.
- **VALIDATE**: `cd services/rag-service && uv run pytest -q`

### UPDATE worker backend client with internal service token

- **IMPLEMENT**: Add header injection to `worker/services/backend_client.py` on calls to task-service.
- **PATTERN**: existing HTTP client methods in `worker/services/backend_client.py:16-44`.
- **IMPORTS**: worker config field for internal token.
- **GOTCHA**: ensure token exists in compose env for worker containers.
- **VALIDATE**: `cd worker && uv run pytest tests/test_main.py tests/test_agent.py -v`

### UPDATE frontend login and bearer propagation

- **IMPLEMENT**: Replace placeholder login behavior in `frontend/src/app/login/page.tsx` with auth API call; add centralized bearer token attach + refresh flow.
- **PATTERN**: current route-driven navigation in `frontend/src/features/workspace/WorkspaceShell.tsx`.
- **IMPORTS**: new API helper/auth store.
- **GOTCHA**: avoid tight coupling to temporary prototype routes.
- **VALIDATE**: `cd frontend && npm run build`

### ADD cross-user authorization tests

- **IMPLEMENT**: Two-user scenarios asserting forbidden/hidden access across project/conversation/task/run/artifact/rag.
- **PATTERN**: async API tests style in `services/task-service/tests/test_models_api.py:72-113`.
- **IMPORTS**: `pytest`, `AsyncClient`, fixtures for two users and owned resources.
- **GOTCHA**: include both list and detail endpoint assertions.
- **VALIDATE**: `uv run pytest services/task-service/tests services/auth-service/src/test -v`

---

## TESTING STRATEGY

### Unit Tests

Scope:
- Java auth-service token/password/session logic.
- Python auth dependency parser and owner check helper functions.

Requirements:
- Deterministic expiry/rotation tests.
- Hash verification and invalid hash/token cases.

### Integration Tests

Scope:
- Register/login/refresh/logout/me flows.
- End-to-end owner scoping in project/task/rag services.
- Worker event ingestion with internal token.

Requirements:
- Two-user fixture setup.
- Negative tests for cross-user access on list + detail + mutation.

### Edge Cases

- Duplicate email registration.
- Expired access token.
- Replayed refresh token after rotation.
- Missing internal service token for worker callback endpoints.
- Legacy project rows without owner during migration window.
- Invalid issuer/audience JWT from external caller.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Build & Syntax

```bash
cd services/auth-service && mvn -q -DskipTests package
cd services/project-service && uv run python -m compileall app
cd services/task-service && uv run python -m compileall app
cd services/rag-service && uv run python -m compileall app
cd worker && uv run python -m compileall .
```

### Level 2: Unit Tests

```bash
cd services/auth-service && mvn -q test
cd services/task-service && uv run pytest tests/test_models_api.py -v
```

### Level 3: Integration Tests

```bash
cd backend && uv run alembic upgrade head
docker compose up --build -d
curl -s http://localhost/health
curl -s http://localhost/api/auth/health
curl -s http://localhost/api/projects -H "Authorization: Bearer <token>"
```

### Level 4: Manual Validation

```bash
# 1) Register user A and user B
# 2) User A creates project + conversation
# 3) User B attempts to read A resources (must fail per policy)
# 4) User A creates task/run and verifies run stream still functions
# 5) Verify worker can emit run events with internal service token header
```

### Level 5: Migration Safety

```bash
cd backend && uv run alembic current
cd backend && uv run alembic downgrade -1
cd backend && uv run alembic upgrade head
```

---

## ACCEPTANCE CRITERIA

- [ ] Java `auth-service` is added and runs in compose.
- [ ] Register/login/refresh/logout/me APIs function with tests.
- [ ] `projects.owner_user_id` exists, indexed, and is non-null after migration.
- [ ] Project and conversation endpoints are owner-scoped.
- [ ] Task/run/artifact endpoints are owner-scoped.
- [ ] RAG project endpoints are owner-scoped.
- [ ] Worker callback and artifact upload internal APIs remain functional via internal token.
- [ ] Gateway routes `/api/auth` and `/api/users` correctly.
- [ ] Frontend login flow obtains token and protected APIs use bearer token.
- [ ] No regressions in queue-driven run execution flow.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (Java + Python services)
- [ ] No linting/type/build errors
- [ ] Manual multi-user validation completed
- [ ] Acceptance criteria all met
- [ ] Security configuration documented for deployment

---

## NOTES

### Design Decisions

- Auth remains an independent domain service (Java) while business services stay Python.
- Ownership root is project-level to minimize schema churn and match existing resource graph.
- Services verify JWT locally for performance and resiliency.
- Internal callbacks are secured separately to avoid coupling worker with user sessions.

### Trade-offs

- Mixed-language stack increases operational complexity, but minimizes rewrite risk and delivery time.
- Shared DB remains in place for MVP speed; stricter service DB isolation can follow later.

### Known Implementation Risks

- Migration discipline is mandatory; `create_all` is insufficient for existing data.
- Misconfigured JWT claims between services can cause broad auth failures.
- Frontend is in active refactor; keep auth adapter thin and centralized.

### Confidence Score

**8.7 / 10** that implementation can be completed in one pass with this plan.

