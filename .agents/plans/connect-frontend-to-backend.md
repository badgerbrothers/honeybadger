# Feature: Connect Frontend To Backend (Auth + Workspace + Runs + RAG)

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Wire the existing Next.js frontend (currently driven by local mock state in `WorkspaceContext`/`RagContext`) to the running microservices baseline (`services/*` behind `nginx/`).

Outcome: a user can register/login, create/select projects and conversations, send messages that create tasks and runs, watch run events via WebSocket, and manage RAG collections and file uploads.

## User Story

As a signed-in user
I want to use the web UI to create projects/conversations, execute tasks, and manage RAG knowledge
So that I can run the full Badgers MVP workflow end-to-end without relying on mock data.

## Problem Statement

Frontend pages are present but rely on in-memory seed data (`WorkspaceContext.tsx`, `RagContext.tsx`) and fake auth (`AuthPage.tsx` form posts to `/dashboard`). The backend already exposes authenticated APIs and realtime run streaming, but the frontend has no API client, no auth/token storage, no data cache, and no websocket wiring.

## Solution Statement

Add a small frontend platform layer:

- `AuthProvider`: manage access/refresh tokens via auth-service endpoints and expose current user.
- `ApiClient`: `fetch` wrapper that injects bearer token, refreshes on 401, and normalizes errors.
- `QueryClientProvider`: cache server state with TanStack React Query.
- `RunStream`: connect to `WS /api/runs/{run_id}/stream?token=...` and update UI in real time.

Then refactor existing UI contexts/pages to call backend APIs:

- Workspace: projects/conversations/messages/tasks via project-service + task-service.
- Dashboard: tasks kanban via task-service queue-status + kanban endpoints.
- RAG: collections/files via rag-service, and project binding via project-service.
- Artifacts: list per run and download via authenticated fetch.

## Feature Metadata

**Feature Type**: Enhancement / Refactor (UI + integration)
**Estimated Complexity**: High
**Primary Systems Affected**: `frontend/` (Next.js app), auth-service, project-service, task-service, rag-service (via existing endpoints)
**Dependencies**:
- Existing backend gateway path routing: [nginx.conf](/F:/Programs/project_4/nginx/nginx.conf)
- Existing auth endpoints: `services/auth-service` controllers
- React Query already present in deps but not wired: [package.json](/F:/Programs/project_4/frontend/package.json)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `frontend/src/features/auth/AuthPage.tsx` (lines 12-106) - Fake auth form; must be replaced with real `/api/auth/*` calls.
- `frontend/src/features/workspace/WorkspaceContext.tsx` (lines 11-200+) - Mock seed state for projects/conversations/messages/tasks; must be replaced with backend-driven state.
- `frontend/src/app/(workspace)/conversation/page.tsx` (lines 14-210+) - Calls `sendMessage()` from mock context; must become async flow: message -> task -> run.
- `frontend/src/app/(workspace)/dashboard/page.tsx` (lines 12-200+) - Kanban expects `TaskStatus` of `schedule|queue|inprogress|done`; backend uses `queue_status` enum (`scheduled|queued|in_progress|done`).
- `services/auth-service/src/main/java/com/badgers/auth/controller/AuthController.java` - Auth endpoints: `/api/auth/register|login|refresh|logout`.
- `services/auth-service/src/main/java/com/badgers/auth/controller/UserController.java` - Current user endpoint `/api/users/me`.
- `services/task-service/app/routers/tasks.py` (lines 117-246+) - Task CRUD, `GET /models`, `GET /kanban`, `PATCH /{task_id}/queue-status`, `POST /{task_id}/runs`.
- `services/task-service/app/routers/runs.py` (lines 44-133) - `GET /runs/{id}`, `GET /runs/{id}/artifacts`, `POST /runs/{id}/cancel`, `WS /runs/{id}/stream`.
- `services/project-service/app/routers/projects.py` (lines 41-220) - Projects + project file upload + file list + artifacts list.
- `services/project-service/app/routers/conversations.py` (lines 34-143) - Conversations + messages CRUD.
- `services/project-service/app/routers/project_rag.py` - Project <-> active global RAG binding.
- `services/rag-service/app/routers/rag_collections.py` (lines 50-214) - Global RAG collections + file upload + list.
- `docker-compose.yml` - Confirms `NEXT_PUBLIC_API_URL=http://localhost/api` and `NEXT_PUBLIC_WS_URL=ws://localhost` for frontend.

### New Files to Create

- `frontend/src/app/providers.tsx` - QueryClientProvider + AuthProvider composition.
- `frontend/src/lib/config.ts` - Resolve `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` with sane defaults for local dev.
- `frontend/src/lib/auth/AuthContext.tsx` - Token storage + `login/register/refresh/logout` + `useAuth`.
- `frontend/src/lib/api/client.ts` - `apiFetch` wrapper with refresh-on-401 and typed helpers.
- `frontend/src/lib/api/types.ts` - Shared DTOs mirroring backend schemas (Project, Conversation, Message, Task, TaskRun, Artifact, RagCollection, RagFile, ModelCatalog).
- `frontend/src/lib/api/endpoints.ts` - Concrete functions per domain (projects/conversations/tasks/runs/artifacts/rags).
- `frontend/src/lib/ws/runStream.ts` - WebSocket helper for run stream.
- `frontend/src/lib/download.ts` - Download helper using auth fetch + Blob save.
- `frontend/src/app/(workspace)/runs/[runId]/page.tsx` - Run viewer page (status, events, artifacts).

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- Next.js App Router data fetching:
  - https://nextjs.org/docs/app/building-your-application/data-fetching/fetching
  - Why: Keep all backend calls in client components using our API client, avoid server-only access to localStorage tokens.
- TanStack Query (React):
  - https://tanstack.com/query/latest/docs/framework/react/overview
  - Why: Standard pattern for server state caching + invalidation after mutations.
- WebSocket API:
  - https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
  - Why: Correct lifecycle, cleanup, and reconnection patterns.

### Patterns to Follow

**Backend auth pattern:** all service endpoints use FastAPI `HTTPBearer` and expect `Authorization: Bearer <accessToken>`.
- Example: `services/task-service/app/security/auth.py` - `get_current_user()` decodes access token.

**Queue status naming (backend):** `QueueStatus` is `scheduled|queued|in_progress|done`.
- Example: `services/task-service/app/models/task.py` - `QueueStatus` enum.

**Run stream contract:** websocket requires `token` query param and sends broadcast events appended to `TaskRun.logs`.
- Example: `services/task-service/app/routers/runs.py` (lines 110-133).

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Add frontend providers and API/auth layers so all subsequent work uses consistent primitives.

Tasks:
- Add `Providers` in root layout.
- Add `AuthProvider` and token storage.
- Add `ApiClient` wrapper with refresh-on-401.
- Add `RunStream` helper.

### Phase 2: Core Implementation

Refactor current pages/contexts to use backend APIs and stop relying on in-memory mock state.

Tasks:
- Replace fake auth in `AuthPage`.
- Refactor `WorkspaceContext` to backend-driven state (projects, conversations, messages, tasks).
- Wire `ConversationPage` send flow: create message -> create task -> create run -> navigate to run viewer.
- Wire `DashboardPage` to `/api/tasks/kanban` + `/api/tasks/{id}/queue-status`.

### Phase 3: Integration

Enable artifacts and RAG management in UI.

Tasks:
- Run viewer page with websocket and artifacts list + download.
- Replace `RagContext` mock with `/api/rags` and `/api/rags/{id}/files`.
- Implement file uploads for RAG and for project files.
- Add project active RAG binding UI (PUT `/api/projects/{id}/rag`).

### Phase 4: Testing & Validation

Add fast validations for frontend correctness and a manual e2e checklist.

Tasks:
- Type-check and lint frontend.
- Optional: basic unit tests around API client error/refresh handling (vitest).
- Manual flow verification against docker-compose.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE `frontend/src/lib/config.ts`
- **IMPLEMENT**: Export `API_BASE_URL` and `WS_BASE_URL` with defaults (`http://localhost/api`, `ws://localhost`).
- **GOTCHA**: Keep this client-safe (no server-only APIs).
- **VALIDATE**: `cd frontend; npm run type-check`

### CREATE `frontend/src/lib/auth/AuthContext.tsx`
- **IMPLEMENT**: Token persistence (localStorage), `login/register/refresh/logout`, `getAccessToken()`, `useAuth()`.
- **PATTERN**: Auth endpoints from `AuthController.java`.
- **GOTCHA**: `JWT_SECRET` must be >= 32 bytes in runtime env; otherwise auth-service will fail to boot.
- **VALIDATE**: `cd frontend; npm run type-check`

### CREATE `frontend/src/lib/api/client.ts`
- **IMPLEMENT**: `apiFetch(path, { method, body, headers })` that:
  - prepends `API_BASE_URL`
  - injects `Authorization` header
  - on 401, calls `refresh()` then retries once
  - parses JSON + blob responses
  - throws normalized error object for UI
- **VALIDATE**: `cd frontend; npm run type-check`

### CREATE `frontend/src/app/providers.tsx` + UPDATE `frontend/src/app/layout.tsx`
- **IMPLEMENT**: QueryClientProvider + AuthProvider + (optional) global error boundary.
- **PATTERN**: Next App Router client providers pattern.
- **VALIDATE**: `cd frontend; npm run build`

### UPDATE `frontend/src/features/auth/AuthPage.tsx`
- **IMPLEMENT**: Replace `<form action="/dashboard">` with controlled form and `auth.login/register`.
- **IMPLEMENT**: On success redirect to `/conversation`.
- **VALIDATE**: `cd frontend; npm run type-check`

### REFACTOR `frontend/src/features/workspace/WorkspaceContext.tsx`
- **REMOVE**: all seed/mock data and `Math.random()` ids.
- **ADD**: React Query-backed fetch + mutations:
  - projects: `GET/POST/PATCH/DELETE /api/projects`
  - conversations: `GET/POST/PATCH/DELETE /api/conversations?project_id=...`
  - messages: `GET/POST /api/conversations/{id}/messages`
  - tasks: `GET /api/tasks?conversation_id=...` and/or `GET /api/tasks/kanban?project_id=...`
- **GOTCHA**: Convert backend UUIDs to string and store in state; keep `active*Id` stable across refetches.
- **VALIDATE**: `cd frontend; npm run type-check`

### UPDATE `frontend/src/app/(workspace)/conversation/page.tsx`
- **ADD**: Model list from `GET /api/tasks/models` and select.
- **CHANGE**: send flow becomes async:
  1. `POST /api/conversations/{id}/messages` (role=user)
  2. `POST /api/tasks` (goal=message, project_id, conversation_id, model, rag_collection_id)
  3. `POST /api/tasks/{task_id}/runs`
  4. navigate to `/runs/{run_id}`
- **ADD**: Attachment upload to `POST /api/projects/{project_id}/files/upload` (uses bearer token).
- **VALIDATE**: `cd frontend; npm run type-check`

### UPDATE `frontend/src/app/(workspace)/dashboard/page.tsx`
- **CHANGE**: Load board from `GET /api/tasks/kanban?project_id=...`.
- **CHANGE**: DnD updates via `PATCH /api/tasks/{id}/queue-status?queue_status=...`.
- **GOTCHA**: Map UI statuses (`schedule|queue|inprogress|done`) <-> backend (`scheduled|queued|in_progress|done`).
- **VALIDATE**: `cd frontend; npm run type-check`

### CREATE `frontend/src/app/(workspace)/runs/[runId]/page.tsx`
- **IMPLEMENT**: Run status view:
  - `GET /api/runs/{runId}` initial
  - websocket subscribe to append events
  - list artifacts `GET /api/runs/{runId}/artifacts`
  - download artifact via authenticated fetch from `/api/artifacts/{id}/download`
  - cancel run `POST /api/runs/{runId}/cancel`
- **VALIDATE**: `cd frontend; npm run build`

### REFACTOR `frontend/src/features/rag/RagContext.tsx` + UPDATE RAG pages
- **REMOVE**: seed/mock rags/files.
- **ADD**: React Query hooks:
  - list/create/update/delete rag collections via `/api/rags`
  - list/upload rag files via `/api/rags/{rag_id}/files` + `/upload`
- **ADD**: Project binding UI using `/api/projects/{project_id}/rag`.
- **VALIDATE**: `cd frontend; npm run type-check`

---

## TESTING STRATEGY

### Unit Tests
- Add small `vitest` tests for `apiFetch` refresh-on-401 behavior using mocked fetch.

### Integration Tests
- Manual integration via docker compose (fastest signal for this repo’s architecture).

### Edge Cases
- Expired access token triggers refresh and original request retry.
- 401 on refresh triggers logout and redirect to `/login`.
- WebSocket token invalid closes with 4401; UI should show “session expired” and prompt relogin.
- File upload size/type errors from backend are shown as user-readable messages.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style
- `cd frontend; npm run lint`
- `cd frontend; npm run type-check`

### Level 2: Unit Tests
- `cd frontend; npm test`

### Level 3: Integration Tests
- (Optional, backend) `cd backend; uv run pytest -q` (legacy)

### Level 4: Manual Validation
1. `docker compose up --build -d`
2. Open `http://localhost:3000`
3. Register + login
4. Create project + conversation
5. Send message -> task created -> run created -> navigate to run page
6. Observe realtime events via WS
7. Verify artifacts appear, download works
8. Create RAG collection, upload file, bind to project, upload project file triggers indexing job

---

## ACCEPTANCE CRITERIA

- [ ] Auth UI uses real backend endpoints and persists JWT tokens
- [ ] All authenticated API calls include bearer token and auto-refresh on 401
- [ ] Projects/conversations/messages are loaded from backend and mutations reflect immediately in UI
- [ ] Sending a message creates a task + run and navigates to a run page
- [ ] Run page shows realtime events from websocket and lists artifacts
- [ ] Dashboard reflects backend kanban and supports queue-status updates
- [ ] RAG page manages collections and file uploads via rag-service
- [ ] `npm run lint`, `npm run type-check`, `npm test` pass

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Manual end-to-end flow verified against compose

---

## NOTES

- Current frontend has no API hooks; integration requires new `lib/` layer and provider wiring.
- There are existing unstaged frontend edits in `frontend/src/app/rag/rag.css` and `frontend/src/features/rag/RagSidebar.tsx`; rebase the RAG work on top of them instead of overwriting.

**Confidence Score**: 7/10 (big refactor surface area, but backend endpoints and routing are already in place)

