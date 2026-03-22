# Feature: Frontend Model Selection with Config-Driven Defaults

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Enable users to explicitly choose the task model from the frontend, ensure the selected model is sent to backend task creation, and guarantee backend/worker execution uses that selected model. When users do not pick a model, the system must initialize and fall back to a configured default model (`DEFAULT_MAIN_MODEL`) rather than hardcoded literals.

## User Story

As a task operator
I want to choose which model a task uses from the frontend
So that task execution uses my chosen model, while still having a safe configured default when I do not choose one

## Problem Statement

Current model selection behavior is only partially configurable:

1. Frontend conversation page uses a free-text model input with a hardcoded initial state (`gpt-5.3-codex`), which is not configuration-driven.
2. Task-service model default is currently hardcoded at ORM layer (`Task.model` default literal), which couples runtime behavior to source code instead of environment configuration.
3. Backend does not enforce model validity against a shared supported-model set, so invalid model strings can pass into persisted tasks and fail later during worker execution.
4. There is no dedicated API for frontend to discover default model + supported models, making model selection UX fragile and duplicated.

## Solution Statement

Implement a configuration-driven model contract across frontend -> task-service -> worker:

1. Add task-service runtime settings for `default_main_model` and `supported_models`.
2. Add task-service API endpoint exposing model metadata (default + supported list).
3. Update task creation flow to resolve model as:
   - `request.model` if provided and valid
   - else `settings.default_main_model`
4. Remove hardcoded ORM default literals for `Task.model` in active service path and rely on API-level assignment + DB non-null enforcement.
5. Update frontend to render a model select bound to metadata endpoint; initialize UI default from backend config result.
6. Keep worker execution behavior (`task.model or settings.default_main_model`) but add compatibility test coverage for empty-model legacy rows.

## Feature Metadata

**Feature Type**: Enhancement/Refactor
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- `frontend` conversation task creation UI
- `services/task-service` config/router/schema/model path
- `worker` model routing safety/compatibility tests
- Environment configuration (`.env.example`, `docker-compose.yml`)

**Dependencies**:
- FastAPI + Pydantic settings (task-service)
- Next.js + React Query (frontend)
- Worker model registry/router (`worker/models/*`)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `frontend/src/app/conversations/[id]/page.tsx:21` - Current task-create form state and model input (`useState('gpt-5.3-codex')` + free text input).
- `frontend/src/features/tasks/api/tasks.ts:19` - Task creation API call wrapper.
- `frontend/src/lib/types.ts:77` - `CreateTaskInput` supports optional `model`.
- `services/task-service/app/routers/tasks.py:25` - `create_task` currently persists with `Task(**task.model_dump())` directly.
- `services/task-service/app/schemas/task.py:7` - `TaskCreate` model input schema currently has optional string `model` but no normalization/validation against registry.
- `services/task-service/app/models/task.py:26` - Hardcoded ORM default for `Task.model` currently set to literal.
- `services/task-service/app/config.py:6` - Service settings class currently missing `default_main_model` + supported models settings.
- `worker/main.py:378` - Worker runtime uses `task.model or settings.default_main_model` during provider creation.
- `worker/config.py:25` - Worker default model config source.
- `worker/models/registry.py:5` - Supported model registry to mirror/consume.
- `worker/models/router.py:13` - Model validation behavior (`Unsupported model`).
- `worker/models/factory.py:33` - Provider routing from model name.
- `.env.example:30` - Current global default model env var.
- `docker-compose.yml:220` - `DEFAULT_MAIN_MODEL` passed to worker; currently not passed to task-service.

### New Files to Create

- `services/task-service/app/schemas/model_catalog.py` - Response schemas for model metadata endpoint.
- `services/task-service/tests/test_models_api.py` - API tests for default model resolution, explicit model selection, invalid model rejection, and metadata endpoint.
- `frontend/src/features/tasks/api/models.ts` - Frontend API client for fetching model metadata.
- `frontend/src/features/tasks/hooks/useModelCatalog.ts` - React Query hook for model metadata.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI - Query Parameters and Validation](https://fastapi.tiangolo.com/tutorial/query-params/)
  - Specific section: parameter validation and response modeling
  - Why: needed for robust model metadata and create-task validation behavior.
- [Pydantic Settings (pydantic-settings)](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
  - Specific section: environment parsing for complex settings
  - Why: needed to parse supported model list from env and keep defaults configurable.
- [React Query (TanStack Query) - useQuery](https://tanstack.com/query/latest/docs/framework/react/reference/useQuery)
  - Specific section: dependent/default query states
  - Why: required for model catalog fetch + default selection lifecycle.
- [Next.js App Router Client Components](https://nextjs.org/docs/app/building-your-application/rendering/client-components)
  - Specific section: client state and form interactions
  - Why: aligns model select behavior with existing conversation page.

### Patterns to Follow

**FastAPI Router Pattern** (existing):

- `services/task-service/app/routers/tasks.py:12`

```python
router = APIRouter(prefix="/api/tasks", tags=["tasks"])
```

- `services/task-service/app/routers/tasks.py:25`

```python
@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(...):
```

**Frontend API Wrapper Pattern**:

- `frontend/src/features/tasks/api/tasks.ts:19`

```ts
return request<Task>('/tasks/', {
  method: 'POST',
  body: JSON.stringify(data),
});
```

**Worker Model Routing Pattern**:

- `worker/models/router.py:18`

```python
def route(self, model: str) -> ProviderType:
    normalized = self.normalize_model_name(model)
    self.validate_model(normalized)
    return get_provider_for_model(normalized)
```

**Current Frontend Form Pattern**:

- `frontend/src/app/conversations/[id]/page.tsx:46`

```ts
const payload = { ... } as { ...; model?: string };
if (normalizedModel) payload.model = normalizedModel;
```

**Error Handling Pattern**:

- Use `HTTPException(status_code=422, detail=...)` in service validation path.
- Frontend request errors already flow through `ApiClientError` in `frontend/src/lib/api.ts:26`.

---

## IMPLEMENTATION PLAN

### Phase 1: Configuration and Contract Foundation

Define a single source of truth for default model and supported models in task-service.

**Tasks:**

- Add task-service settings for `default_main_model` and `supported_models`.
- Add normalization helper for model names (trim/lower compare, preserve canonical output).
- Add API schema for model metadata response.

### Phase 2: Backend API and Validation

Implement create-task resolution and model catalog endpoint.

**Tasks:**

- Update `create_task` to resolve model from request or configured default.
- Validate selected/default model against supported catalog before DB write.
- Add `GET /api/tasks/models` returning:
  - `default_model`
  - `supported_models`
- Remove ORM hardcoded default for active task-service model field and keep non-null semantics.

### Phase 3: Frontend Model Selection UX

Replace free-text model behavior with config-driven select and submission.

**Tasks:**

- Fetch model catalog from backend.
- Initialize local model state from `default_model` once loaded.
- Render select options from `supported_models`.
- Submit chosen model explicitly in `createTask` payload.

### Phase 4: Worker and Cross-Service Compatibility

Ensure worker behavior remains deterministic for legacy and new data.

**Tasks:**

- Keep worker execution precedence (`task.model` first, fallback default second).
- Add/adjust tests for model routing and unsupported model rejection.
- Add regression check for legacy rows where `task.model` may be null/empty during migration windows.

### Phase 5: Testing and Validation

Add targeted service and frontend tests plus runtime smoke flow.

**Tasks:**

- Add task-service API tests for model logic.
- Add frontend unit tests for default initialization and payload behavior.
- Run docker-based manual flow to verify end-to-end selection effect.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE `services/task-service/app/config.py`

- **IMPLEMENT**: Add `default_main_model: str` and `supported_models: str` or parsed list setting (e.g., comma-separated env var).
- **PATTERN**: `Settings(BaseSettings)` in `services/task-service/app/config.py:6`.
- **IMPORTS**: `Field` already used; add helpers as needed.
- **GOTCHA**: Keep env-file behavior unchanged (`SettingsConfigDict(env_file=".env", extra="ignore")`).
- **VALIDATE**: `uv run --project services/task-service python -c "from app.config import settings; print(settings.default_main_model)"`

### CREATE `services/task-service/app/schemas/model_catalog.py`

- **IMPLEMENT**: Add Pydantic response models (e.g., `ModelCatalogResponse`).
- **PATTERN**: Schema style from `services/task-service/app/schemas/task.py:1`.
- **IMPORTS**: `BaseModel`, `Field` if needed.
- **GOTCHA**: Keep schema names explicit and API-facing.
- **VALIDATE**: `uv run --project services/task-service python -c "from app.schemas.model_catalog import ModelCatalogResponse; print('ok')"`

### UPDATE `services/task-service/app/routers/tasks.py`

- **IMPLEMENT**:
  - Add model normalization + validation helper.
  - In `create_task`, resolve model from request or config default before constructing `Task`.
  - Return `422` for unsupported models.
  - Add `GET /api/tasks/models` endpoint for frontend discovery.
- **PATTERN**: Existing router and error patterns in same file (`tasks.py:12`, `tasks.py:25`).
- **IMPORTS**: `settings` from config, new schema, optional worker-compatible model list source.
- **GOTCHA**: Ensure no behavior regressions for queue/run endpoints.
- **VALIDATE**: `uv run --project services/task-service python -c "from app.routers import tasks; print('ok')"`

### UPDATE `services/task-service/app/models/task.py`

- **IMPLEMENT**: Remove hardcoded Python-side default literal from `Task.model` and rely on API assignment.
- **PATTERN**: Existing non-null mapped column declaration in `services/task-service/app/models/task.py:26`.
- **GOTCHA**: Keep column nullable=False; migration impact must be handled (no null insert path).
- **VALIDATE**: `uv run --project services/task-service python -c "from app.models.task import Task; print(Task.__table__.c.model.nullable)"`

### UPDATE `docker-compose.yml`

- **IMPLEMENT**: Pass `DEFAULT_MAIN_MODEL` (and optional `SUPPORTED_MODELS`) to `task-service` environment block.
- **PATTERN**: Worker env injection style at `docker-compose.yml:220`.
- **GOTCHA**: Use `${VAR:-default}` style to preserve local workflows.
- **VALIDATE**: `docker compose config > NUL`

### UPDATE `.env.example`

- **IMPLEMENT**: Document `DEFAULT_MAIN_MODEL` and `SUPPORTED_MODELS` usage for frontend/backend model selection.
- **PATTERN**: Existing model section at `.env.example:24`.
- **GOTCHA**: Keep secrets placeholders unchanged.
- **VALIDATE**: `rg -n "DEFAULT_MAIN_MODEL|SUPPORTED_MODELS" .env.example`

### CREATE `frontend/src/features/tasks/api/models.ts`

- **IMPLEMENT**: Add request wrapper function for `GET /tasks/models`.
- **PATTERN**: API style from `frontend/src/features/tasks/api/tasks.ts:1`.
- **IMPORTS**: `request` and typed response.
- **VALIDATE**: `cd frontend; npm run type-check`

### CREATE `frontend/src/features/tasks/hooks/useModelCatalog.ts`

- **IMPLEMENT**: React Query hook for model catalog retrieval.
- **PATTERN**: Hook style from existing hooks (e.g., `useTasks`, `useConversation`).
- **GOTCHA**: Avoid repeated state reset when query refetches.
- **VALIDATE**: `cd frontend; npm run type-check`

### UPDATE `frontend/src/app/conversations/[id]/page.tsx`

- **IMPLEMENT**:
  - Replace free-text model input with select/dropdown bound to model catalog.
  - Initialize model state from backend `default_model` (only once when available).
  - Ensure payload always sends selected model.
- **PATTERN**: Mutation payload assembly in `page.tsx:46`.
- **GOTCHA**: Preserve current behavior for skill and goal validation.
- **VALIDATE**: `cd frontend; npm run type-check`

### UPDATE `frontend/src/lib/types.ts`

- **IMPLEMENT**: Add type definitions for model catalog response.
- **PATTERN**: Existing API type contracts in same file.
- **VALIDATE**: `cd frontend; npm run type-check`

### ADD TESTS `services/task-service/tests/test_models_api.py`

- **IMPLEMENT** test cases:
  - create task with explicit supported model -> persists model
  - create task without model -> defaults to config model
  - create task with unsupported model -> 422
  - list model catalog endpoint returns default + supported list
- **PATTERN**: Async API tests style in `backend/tests/test_api_tasks.py:6`.
- **GOTCHA**: isolate DB state and avoid dependency on external model providers.
- **VALIDATE**: `uv run --project services/task-service pytest services/task-service/tests/test_models_api.py -q`

### UPDATE/ADD FRONTEND TESTS

- **IMPLEMENT**:
  - component/unit test for conversation model select default initialization
  - task payload includes selected model
- **PATTERN**: Vitest setup in `frontend/vitest.config.ts:9`; sample test style in `frontend/src/features/tasks/components/__tests__/TaskKanbanBoard.test.tsx`.
- **VALIDATE**: `cd frontend; npm test -- --runInBand`

---

## TESTING STRATEGY

### Unit Tests

- Task-service model resolution helper and validation helper.
- Worker model router compatibility (existing tests in `worker/tests/test_model_router.py`).
- Frontend model catalog hook and model payload assembly.

### Integration Tests

- Task-service endpoint tests for create-task + model catalog.
- Docker compose smoke flow:
  - fetch model catalog
  - create task with selected model
  - create run and inspect task/run payload consistency.

### Edge Cases

- User provides model with extra whitespace/case differences.
- Config default model not present in supported list.
- Empty supported models env var.
- Legacy task row with null/empty model reaches worker path.
- Frontend catalog fetch failure should not crash task form.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and feature correctness.

### Level 1: Syntax & Style

```bash
uv run --project services/task-service python -m py_compile services/task-service/app/config.py services/task-service/app/routers/tasks.py services/task-service/app/schemas/model_catalog.py
cd frontend && npm run type-check
```

### Level 2: Unit Tests

```bash
uv run --project services/task-service pytest services/task-service/tests/test_models_api.py -q
cd worker && uv run pytest tests/test_model_registry.py tests/test_model_router.py tests/test_models_factory.py -q
cd frontend && npm test
```

### Level 3: Integration Tests

```bash
docker compose up -d --build task-service worker-taskrun api-gateway
curl http://localhost/api/tasks/models
```

### Level 4: Manual Validation

```bash
# 1) Open conversation page and confirm model dropdown defaults to API default_model
# 2) Create task and verify task.model in API response matches selected option
curl -X POST http://localhost/api/tasks/ -H "Content-Type: application/json" -d '{"conversation_id":"<id>","project_id":"<id>","goal":"model check","model":"gpt-5.3-codex"}'
# 3) Create task without model and verify default applied
curl -X POST http://localhost/api/tasks/ -H "Content-Type: application/json" -d '{"conversation_id":"<id>","project_id":"<id>","goal":"default check"}'
# 4) Unsupported model should fail
curl -X POST http://localhost/api/tasks/ -H "Content-Type: application/json" -d '{"conversation_id":"<id>","project_id":"<id>","goal":"bad model","model":"unknown-model"}'
```

### Level 5: Additional Validation (Optional)

```bash
# verify compose env wiring
docker compose exec -T task-service python -c "from app.config import settings; print(settings.default_main_model)"
```

---

## ACCEPTANCE CRITERIA

- [ ] Frontend presents model selection control backed by API model catalog.
- [ ] Selected model is always sent in task creation payload.
- [ ] Task-service uses selected model when provided.
- [ ] Task-service falls back to `DEFAULT_MAIN_MODEL` when request omits model.
- [ ] Unsupported model values are rejected with 422 before persistence.
- [ ] Worker execution uses persisted `task.model` and only falls back for legacy empty/null data.
- [ ] No hardcoded default-model literal remains in active task-service task model field.
- [ ] Validation commands pass.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Targeted test suites pass (task-service + worker + frontend)
- [ ] No lint/type errors introduced
- [ ] Manual UI/API checks confirm selected/default model behavior
- [ ] Acceptance criteria all met

---

## NOTES

- Current worker model registry is under `worker/models/registry.py`; task-service should avoid importing worker runtime internals directly if that creates dependency coupling. Prefer one of:
  - introducing a shared model catalog module under `shared/`, or
  - configuring supported models via env (`SUPPORTED_MODELS`) and validating against it in task-service.
- Keep backward compatibility for existing tasks created before this change.
- Because model provider access can be blocked by external gateway policy, functional verification of "selection path" should rely on persisted `task.model` and request traces, not only completion status.

**Confidence Score**: 8/10 that execution will succeed on first attempt.
