# Feature: Frontend Product-Oriented Next.js Refactor (From Legacy HTML Prototypes)

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Refactor legacy static HTML prototypes in `html/` into a product-oriented Next.js frontend architecture, aligned with actual Badgers MVP user journeys (project-centric task execution), while preserving existing working flows and APIs.

This is not a 1:1 HTML translation task. The target is to turn mixed prototype pages into a coherent product IA (information architecture), route system, and feature/module boundaries that support long-term evolution.

## User Story

As a technical user delegating multi-step AI work
I want a coherent, product-oriented frontend flow across projects, conversations, tasks, runs, and artifacts
So that I can reliably initiate work, monitor execution, and reuse outputs without navigating disjoint prototype pages.

## Problem Statement

Current frontend has two parallel realities:
- Product code in `frontend/src/app` already supports core flows (`/projects`, `/projects/[id]`, `/conversations/[id]`, `/runs/[id]`, `/tasks/kanban`)
- Legacy static prototypes in `html/` define overlapping, partially inconsistent IA (`dashboard`, `task_kanban`, `execution_split_view`, `artifacts`, `knowledge_base`, `tools_skills`, `settings`, `login`, `index_welcome`)

Because HTML prototypes were produced quickly and include inconsistent naming/links (including stale page references), direct migration would recreate architectural drift. We need a product-first structure that consolidates overlapping concepts and maps only valuable UI patterns into existing feature modules.

## Solution Statement

Adopt a product-usage-driven Next.js App Router refactor with:
1. Clear route hierarchy and shell layout separation (`auth` vs `workspace`)
2. Domain-first feature boundaries (`projects`, `conversations`, `tasks`, `runs`, `artifacts`, `knowledge`, `settings`)
3. Reuse of existing data hooks/API wrappers and loading/error patterns
4. Structured migration of HTML visual patterns into reusable React components
5. Test-first validation for key pages and high-risk interactions

The migration will prioritize end-user workflows over page-by-page HTML parity.

## Feature Metadata

**Feature Type**: Refactor + Enhancement  
**Estimated Complexity**: High  
**Primary Systems Affected**: `frontend/src/app`, `frontend/src/features`, `frontend/src/components/layout`, `frontend/src/lib`, frontend tests  
**Dependencies**: Next.js App Router, TypeScript, Tailwind CSS, TanStack Query, React DnD, existing backend APIs

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `frontend/src/app/layout.tsx` (lines 16-19) - Why: Global provider + header injection pattern currently used by all pages
- `frontend/src/components/layout/Header.tsx` (lines 11-18) - Why: Existing top-nav baseline; currently minimal and needs product nav expansion
- `frontend/src/components/layout/Container.tsx` (lines 5-9) - Why: Shared page width/padding wrapper used across routes
- `frontend/src/components/ui/Card.tsx` (lines 6-10) - Why: Core visual container pattern
- `frontend/src/components/ui/Button.tsx` (lines 14-23) - Why: Existing button variants and class composition style
- `frontend/src/lib/api.ts` (lines 12-35) - Why: Canonical API request/error handling wrapper; must remain single source for JSON APIs
- `frontend/src/lib/query-client.ts` (lines 3-10) - Why: Query defaults (staleTime, retry) to preserve behavior
- `frontend/src/lib/websocket.ts` (lines 15-53, 60-71) - Why: Reconnect behavior and listener model for run event streaming
- `frontend/src/lib/types.ts` (lines 18-47, 51-103) - Why: Canonical frontend DTO contracts for tasks/runs/conversations/artifacts
- `frontend/src/app/page.tsx` (lines 3-4) - Why: Current root redirect behavior (`/ -> /projects`) to revisit during IA redesign
- `frontend/src/app/projects/page.tsx` (lines 18-25) - Why: Existing list/create composition for project home pattern
- `frontend/src/features/projects/components/CreateProjectForm.tsx` (lines 16-44) - Why: Current form validation/mutation pattern
- `frontend/src/features/projects/components/ProjectList.tsx` (lines 7-25) - Why: Standard loading/error/empty handling shape
- `frontend/src/app/projects/[id]/page.tsx` (lines 74-115) - Why: Existing project workspace page already combines conversations + file upload/list
- `frontend/src/features/projects/components/FileUploadZone.tsx` (lines 21-43) - Why: Client-side file validation and upload error pattern
- `frontend/src/app/conversations/[id]/page.tsx` (lines 31-35, 56-96, 210-248) - Why: Task creation/run/retry workflow and mutation invalidation pattern
- `frontend/src/features/tasks/api/tasks.ts` (lines 8-17, 19-35, 38-45) - Why: Task and run API bindings for conversation/run pages
- `frontend/src/features/tasks/api/models.ts` (lines 4-5) - Why: Model catalog endpoint pattern for task creation
- `frontend/src/features/tasks/hooks/useModelCatalog.ts` (lines 5-8) - Why: Query wrapper pattern for catalog data
- `frontend/src/app/runs/[id]/page.tsx` (lines 13-19, 56-96) - Why: Run metadata + event timeline + artifact listing composition
- `frontend/src/features/tasks/components/TaskRunViewer.tsx` (lines 21-33, 56-66) - Why: Status derivation + stream viewer scaffold
- `frontend/src/features/tasks/hooks/useTaskRunStream.ts` (lines 23-39) - Why: WS event dedupe + append logic
- `frontend/src/app/tasks/kanban/page.tsx` (lines 9-13) - Why: Current entry to queue Kanban capability
- `frontend/src/features/tasks/components/TaskKanbanBoard.tsx` (lines 27-57) - Why: Existing DnD board composition and column contract
- `frontend/src/features/tasks/hooks/useTaskKanban.ts` (lines 10-22) - Why: Polling + mutation invalidation approach
- `frontend/src/features/tasks/api/kanban.ts` (lines 11-23) - Why: Queue board fetch/update endpoint bindings
- `frontend/src/features/artifacts/api/artifacts.ts` (lines 6-21) - Why: Artifact list/download/save flow bindings
- `frontend/src/app/conversations/[id]/page.test.tsx` (lines 51-63, 90-119) - Why: Existing provider wrapping and mutation payload assertion style
- `frontend/src/features/tasks/components/__tests__/TaskKanbanBoard.test.tsx` (lines 7-35, 37-45) - Why: Existing mocking strategy for feature hooks
- `.claude/PRD.md` (lines 321-415, 1107-1223) - Why: Product boundaries and success criteria for conversation/task/run/artifact model
- `html/dashboard.html` (lines 180-268) - Why: Prototype “task board” UI blocks and status/action vocabulary
- `html/task_kanban.html` (lines 224-370) - Why: Prototype queue board with card metadata density
- `html/execution_split_view.html` (lines 137-173) - Why: Prototype run split-view (timeline + artifact/code pane)
- `html/artifacts.html` (lines 96-163) - Why: Prototype artifact library list/filters/tag treatment
- `html/index_welcome.html` (lines 290-320) - Why: Prototype “prompt composer + tool toggles” entry concept
- `html/knowledge_base.html` (lines 217+) - Why: Prototype knowledge/memory page direction
- `html/tools_skills.html` (lines 240-326) - Why: Prototype capability center for tools/skills discoverability

### New Files to Create

- `frontend/src/app/(auth)/login/page.tsx` - Product login page replacing `html/login.html` behavior
- `frontend/src/app/(workspace)/layout.tsx` - Workspace shell (left nav + top context region)
- `frontend/src/components/layout/WorkspaceSidebar.tsx` - Shared product navigation component
- `frontend/src/components/layout/workspace-nav.ts` - Central nav config map (labels, routes, permissions flags)
- `frontend/src/app/(workspace)/dashboard/page.tsx` - Product dashboard (merge useful elements from `dashboard.html` + existing task surfaces)
- `frontend/src/app/(workspace)/knowledge/page.tsx` - Knowledge/memory page entry (from `knowledge_base.html`)
- `frontend/src/app/(workspace)/tools/page.tsx` - Tools/skills capability center (from `tools_skills.html`)
- `frontend/src/app/(workspace)/settings/page.tsx` - Settings page migration from static HTML
- `frontend/src/features/dashboard/components/*` - Dashboard widgets (recent runs, queued tasks, quick actions)
- `frontend/src/features/knowledge/components/*` - Knowledge index/search/list scaffolding
- `frontend/src/features/tools/components/*` - Tools/skills cards and grouping UI
- `frontend/src/features/workspace/types.ts` - Shared view models for workspace shell widgets
- `frontend/src/features/workspace/api/*` - API adapters for dashboard/knowledge/tools if needed
- `frontend/src/features/workspace/components/EmptyState.tsx` - Cross-feature empty/error visual consistency
- `frontend/src/app/(workspace)/dashboard/page.test.tsx` - Dashboard render/state tests
- `frontend/src/components/layout/WorkspaceSidebar.test.tsx` - Navigation rendering/active-state tests

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- Internal PRD
  - `.claude/PRD.md` sections:
    - Conversation vs Task Boundary (line 321)
    - Task vs Run Boundary (line 346)
    - Artifact Three-Layer Model (line 383)
    - Success Criteria (line 1107)
  - Why: defines product behavior and resource ownership that UI must represent accurately

- Internal frontend reference
  - `.claude/reference/react-frontend-best-practices.md`
  - Sections:
    - Feature structure (line 27)
    - Data fetching with Query (line 304)
    - Testing patterns (line 1058)
    - Anti-patterns (line 1243)
  - Why: aligns component/module/test conventions with project expectations

- Next.js App Router docs
  - https://nextjs.org/docs/app
  - https://nextjs.org/docs/app/building-your-application/routing/route-groups
  - https://nextjs.org/docs/app/building-your-application/routing/dynamic-routes
  - Why: route groups + dynamic route organization for product shell refactor

- TanStack Query docs
  - https://tanstack.com/query/latest/docs/framework/react/overview
  - https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations
  - Why: cache key design and mutation invalidation during multi-page refactor

- Vitest + Testing Library docs
  - https://vitest.dev/guide/
  - https://testing-library.com/docs/react-testing-library/intro/
  - Why: maintain existing frontend test style and deterministic async assertions

- React DnD docs
  - https://react-dnd.github.io/react-dnd/about
  - Why: preserve and extend queue board drag/drop behavior without regression

### Patterns to Follow

**Naming Conventions:**
- Components: PascalCase (`ProjectCard`, `TaskRunViewer`) as seen in `features/*/components`
- Hooks: `use*` camelCase (`useTaskKanban`, `useModelCatalog`)
- API modules: domain-oriented files under `features/<domain>/api/*.ts`

**Error Handling:**
- API wrapper throws `ApiClientError` from `lib/api.ts:26-31`
- Pages show explicit error copy near data blocks (`ProjectList.tsx:11-17`, `TaskKanbanBoard.tsx:20-22`)

**Logging Pattern:**
- Frontend currently uses `console.error` for WS parse errors (`useTaskRunStream.ts:40-42`) and socket errors (`lib/websocket.ts:30-33`)
- Keep this minimal client logging pattern unless introducing centralized telemetry later

**Other Relevant Patterns:**
- Query + invalidation: mutation success invalidates targeted query key (`useTaskKanban.ts:19-21`, `projects/[id]/page.tsx:31-33`)
- Loading/empty/error triad: repeated and should be standardized, not removed
- Route params via `useParams` with null-safe checks (`runs/[id]/page.tsx:22-27`, `projects/[id]/page.tsx:17-24`)
- Realtime event merge with dedupe by payload fingerprint (`useTaskRunStream.ts:33-39`)
- Tests mock feature hooks/APIs rather than full network (`TaskKanbanBoard.test.tsx:7-35`, `conversations/[id]/page.test.tsx:30-49`)

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Information Architecture + Shell Boundaries)

Define product-first route map and shell architecture before component migration.

**Tasks:**
- Establish canonical workspace IA (auth entry, dashboard, projects, conversations, runs, tasks, artifacts, knowledge, tools, settings)
- Introduce App Router route groups to separate auth shell and workspace shell
- Create config-driven navigation source of truth to avoid hardcoded per-page sidebars
- Decide canonical destinations for each legacy HTML page and mark deprecations

### Phase 2: Core Implementation (Page Refactor by User Journey)

Implement or refactor pages in user flow order instead of HTML file order.

**Tasks:**
- Entry and identity flow (`/login`, root redirect policy)
- Workspace overview (`/dashboard`) with quick actions into projects/tasks/runs
- Execution flow refinement (`/conversations/[id] -> /runs/[id]`)
- Queue flow (`/tasks/kanban`) visual/data parity with legacy prototype where useful
- Artifact and project output flow (`/projects/[id]/artifacts`)
- Capability and memory discoverability (`/tools`, `/knowledge`)
- System configuration (`/settings`)

### Phase 3: Integration (Feature Modules + Data Contracts)

Integrate migrated pages into existing feature modules and API contracts.

**Tasks:**
- Consolidate duplicated UI patterns into reusable feature components
- Keep existing API wrappers and query keys stable where possible
- Add new API adapters only where backend endpoints exist; use explicit TODO mock boundaries otherwise
- Ensure workspace nav highlights active route and keeps context (project/run IDs when needed)

### Phase 4: Testing & Validation

Expand test coverage on high-risk navigation and workflow components.

**Tasks:**
- Add unit/component tests for new shell/nav and dashboard widgets
- Add regression tests for conversation task creation, run viewer, queue board, artifacts actions
- Validate route reachability and no 404s for promoted product pages
- Run full type-check + lint + test suite

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### REFACTOR frontend/src/app (Route Taxonomy + Route Groups)

- **IMPLEMENT**: Introduce route groups for `(auth)` and `(workspace)` and relocate/alias pages based on product flow.
- **PATTERN**: Keep root-level provider pattern from `frontend/src/app/layout.tsx:16-19`.
- **IMPORTS**: `next/navigation`, existing page components from `features/*`.
- **GOTCHA**: Avoid breaking existing deep links (`/projects/[id]`, `/conversations/[id]`, `/runs/[id]`, `/tasks/kanban`) during transition.
- **VALIDATE**: `cd frontend && npm run type-check`

### CREATE frontend/src/components/layout/workspace-nav.ts

- **IMPLEMENT**: Create single nav config object with stable route IDs, labels, href, and optional feature flags.
- **PATTERN**: Replace hardcoded link duplication from legacy HTML sidebars (`html/dashboard.html`, `html/task_kanban.html`, `html/artifacts.html`).
- **IMPORTS**: No React dependency required; pure config module.
- **GOTCHA**: Remove references to stale prototype-only pages (e.g. `manus_clone.html`) from nav model.
- **VALIDATE**: `cd frontend && npm run type-check`

### CREATE frontend/src/components/layout/WorkspaceSidebar.tsx

- **IMPLEMENT**: Render sidebar from nav config with active route styling and responsive collapse behavior.
- **PATTERN**: Existing simple header link style in `frontend/src/components/layout/Header.tsx:11-18`; extend to product nav.
- **IMPORTS**: `next/link`, `next/navigation` (`usePathname`), nav config.
- **GOTCHA**: Ensure keyboard-accessible nav and semantic `<nav>` structure.
- **VALIDATE**: `cd frontend && npm run lint`

### CREATE frontend/src/app/(workspace)/layout.tsx

- **IMPLEMENT**: Add workspace shell composition (`WorkspaceSidebar + content container`) and move workspace pages under this shell.
- **PATTERN**: Keep global `QueryClientProvider` in root layout; workspace layout should not duplicate providers.
- **IMPORTS**: `WorkspaceSidebar`, existing container/layout primitives.
- **GOTCHA**: Prevent nested scroll traps when combining sidebar and long content pages.
- **VALIDATE**: `cd frontend && npm run type-check`

### CREATE frontend/src/app/(auth)/login/page.tsx

- **IMPLEMENT**: Rebuild `html/login.html` as Next.js page with componentized form and clear integration boundary (placeholder/mock if auth API absent).
- **PATTERN**: Controlled form validation style from `CreateProjectForm.tsx:16-44`.
- **IMPORTS**: shared `Card`, `Button`, `Input`.
- **GOTCHA**: Do not fake successful authentication persistence without explicit backend support.
- **VALIDATE**: `cd frontend && npm run test -- src/app/(auth)/login/page.test.tsx`

### CREATE frontend/src/app/(workspace)/dashboard/page.tsx

- **IMPLEMENT**: Build product dashboard by merging useful patterns from `html/dashboard.html` + existing task/run data surfaces.
- **PATTERN**: Loading/error/empty blocks from `ProjectList.tsx:7-25`; card composition from `Card.tsx:6-10`.
- **IMPORTS**: existing task/project APIs/hooks; optional new `features/dashboard` modules.
- **GOTCHA**: Do not duplicate Kanban full board here; dashboard should be summary + deep-link to `/tasks/kanban`.
- **VALIDATE**: `cd frontend && npm run test -- src/app/(workspace)/dashboard/page.test.tsx`

### REFACTOR frontend/src/app/conversations/[id]/page.tsx

- **IMPLEMENT**: Split monolithic conversation page into subcomponents (`MessagePanel`, `TaskComposer`, `TaskListPanel`) while preserving behavior.
- **PATTERN**: Existing mutation/invalidations in lines `44-96`; preserve query keys and side effects.
- **IMPORTS**: maintain current API modules in `features/conversations/api` and `features/tasks/api`.
- **GOTCHA**: Keep explicit Conversation vs Task boundary from PRD (`.claude/PRD.md:321`), i.e., message posting should not auto-create tasks.
- **VALIDATE**: `cd frontend && npm run test -- src/app/conversations/[id]/page.test.tsx`

### REFACTOR frontend/src/app/runs/[id]/page.tsx + features/tasks/components/TaskRunViewer.tsx

- **IMPLEMENT**: Add split-view mode inspired by `html/execution_split_view.html` (timeline + artifact/code context panel) without breaking existing event stream.
- **PATTERN**: Event normalization and status derivation (`runs/[id]/page.tsx:13-19`, `TaskRunViewer.tsx:21-33`).
- **IMPORTS**: `useRunArtifacts`, `buildArtifactDownloadUrl`, event type guards from `features/tasks/types.ts`.
- **GOTCHA**: Ensure initial DB logs and WS incremental events merge deterministically (`useTaskRunStream.ts:33-39`).
- **VALIDATE**: `cd frontend && npm run type-check`

### REFACTOR frontend/src/app/tasks/kanban/page.tsx + features/tasks/components/*

- **IMPLEMENT**: Apply visual density and metadata improvements from `html/task_kanban.html` while keeping existing DnD and queue mutation mechanics.
- **PATTERN**: `TaskKanbanBoard.tsx:27-57`, `useTaskKanban.ts:10-22`, `api/kanban.ts:11-23`.
- **IMPORTS**: `QueueStatus` from `lib/types`, existing column/card components.
- **GOTCHA**: Keep queue status enum compatibility (`scheduled|queued|in_progress|done`) from `lib/types.ts:34`.
- **VALIDATE**: `cd frontend && npm run test -- src/features/tasks/components/__tests__/TaskKanbanBoard.test.tsx`

### REFACTOR frontend/src/app/projects/[id]/artifacts/page.tsx

- **IMPLEMENT**: Enhance artifact library UX based on `html/artifacts.html` (filters/sort/grouping), while preserving real actions (download/save-to-project).
- **PATTERN**: Existing artifact API usage in `features/artifacts/api/artifacts.ts:6-21`.
- **IMPORTS**: `useProjectArtifacts`, `useMutation`, `useQueryClient`.
- **GOTCHA**: Keep action semantics tied to real backend endpoints; do not introduce dead UI controls without support.
- **VALIDATE**: `cd frontend && npm run type-check`

### CREATE frontend/src/app/(workspace)/knowledge/page.tsx and frontend/src/app/(workspace)/tools/page.tsx

- **IMPLEMENT**: Productize `knowledge_base.html` and `tools_skills.html` into discoverability pages; wire to real data if endpoints exist, otherwise explicit placeholder cards.
- **PATTERN**: Feature-first foldering from existing `features/*` modules and shared `Card` usage.
- **IMPORTS**: `Container`, `Card`, potential new feature APIs.
- **GOTCHA**: Mark non-backed interactions clearly (e.g., “coming soon”) to avoid fake functionality.
- **VALIDATE**: `cd frontend && npm run type-check`

### CREATE frontend/src/app/(workspace)/settings/page.tsx

- **IMPLEMENT**: Migrate `settings.html` as structured settings page (model defaults, runtime preferences, UI prefs placeholders if backend missing).
- **PATTERN**: Model catalog API pattern from `features/tasks/api/models.ts:4-5` and `useModelCatalog.ts:5-8`.
- **IMPORTS**: existing UI components and task model API.
- **GOTCHA**: Distinguish between project-level settings and global settings in UI copy and future API contracts.
- **VALIDATE**: `cd frontend && npm run type-check`

### ADD frontend/src/components/layout/WorkspaceSidebar.test.tsx and route smoke tests

- **IMPLEMENT**: Add tests for nav rendering, active route state, and critical route availability.
- **PATTERN**: provider-wrapped rendering style from `conversations/[id]/page.test.tsx:51-63`.
- **IMPORTS**: Testing Library + Vitest setup from `src/test/setup.ts:1`.
- **GOTCHA**: Mock `next/navigation` consistently to avoid flaky active-path assertions.
- **VALIDATE**: `cd frontend && npm run test`

### REMOVE legacy frontend coupling to raw html prototypes

- **IMPLEMENT**: Ensure no frontend runtime route or nav links point to static `html/*.html`; keep `html/` only as reference archive.
- **PATTERN**: Use centralized nav config (`workspace-nav.ts`) as single source of truth.
- **IMPORTS**: N/A
- **GOTCHA**: Do not delete `html/` until migration acceptance is complete.
- **VALIDATE**: `rg -n \"\\.html\\\"|\\.html'\" frontend/src`

---

## TESTING STRATEGY

Follow existing frontend stack (`vitest` + Testing Library + QueryClient provider wrappers) and prioritize workflow reliability over visual snapshot-only testing.

### Unit Tests

- Sidebar/nav config rendering and active state transitions
- Dashboard widgets (loading/error/empty/data)
- Conversation task composer payload behavior (model/skill/goal)
- Run split-view event rendering behavior
- Kanban board card metadata rendering and status transfer callbacks

### Integration Tests

- Conversation detail -> create task -> create run navigation flow
- Run detail loads logs + artifacts and renders timeline state
- Artifact page save-to-project mutation triggers cache invalidation
- Kanban status update invalidates board and refreshes columns

### Edge Cases

- `useParams()` missing values (null-safe guards)
- Empty model catalog or temporary catalog API failure
- WS stream parse failures / disconnect-reconnect loops
- Duplicate run events arriving from historical logs + WS live stream
- Artifacts without `mime_type` or with long names
- Queue board empty columns and large task counts
- Pages with unavailable backend endpoints for tools/knowledge/settings (graceful placeholder UX)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and feature correctness.

### Level 1: Syntax & Style

- `cd frontend && npm run lint`
- `cd frontend && npm run type-check`

### Level 2: Unit Tests

- `cd frontend && npm run test -- src/features/tasks/components/__tests__/TaskKanbanBoard.test.tsx`
- `cd frontend && npm run test -- src/app/conversations/[id]/page.test.tsx`
- `cd frontend && npm run test -- src/components/layout/WorkspaceSidebar.test.tsx`
- `cd frontend && npm run test -- src/app/(workspace)/dashboard/page.test.tsx`

### Level 3: Integration Tests

- `cd frontend && npm run test`

### Level 4: Manual Validation

1. Open `/` and verify redirect/landing behavior aligns with chosen product IA.
2. Open `/projects`, create project, open `/projects/{id}`.
3. Create conversation from project page, land on `/conversations/{id}`.
4. Send message (no implicit task creation), then explicitly create task.
5. Create run and verify navigation to `/runs/{runId}`.
6. Verify run timeline updates and artifact list/download links.
7. Open `/tasks/kanban`, drag task across columns, verify status persists after refresh.
8. Open `/projects/{id}/artifacts`, execute download and save-to-project flow.
9. Open `/dashboard`, `/knowledge`, `/tools`, `/settings` and verify no dead links / no raw `.html` paths.

### Level 5: Additional Validation (Optional)

- `rg -n \"href=.*\\.html|redirect\\('/.*\\.html'\\)\" frontend/src`
- `rg -n \"TODO|coming soon|placeholder\" frontend/src/app/(workspace)`

---

## ACCEPTANCE CRITERIA

- [ ] Frontend route architecture reflects product journeys, not prototype file layout.
- [ ] Legacy HTML concepts are mapped, merged, or explicitly deprecated with rationale.
- [ ] Workspace navigation is centralized and consistent across pages.
- [ ] Core flows remain intact: projects -> conversations -> tasks -> runs -> artifacts.
- [ ] No runtime links in Next.js app point to static `.html` prototype files.
- [ ] New/updated pages implement loading/error/empty states.
- [ ] `npm run type-check`, `npm run lint`, and `npm run test` pass.
- [ ] Existing tests for conversation and kanban behaviors remain green.
- [ ] Added tests cover new nav/shell and dashboard route behavior.
- [ ] UX language and page hierarchy match PRD boundaries (conversation vs task, task vs run, artifact lifecycle).

---

## COMPLETION CHECKLIST

- [ ] Route IA finalized and documented
- [ ] Workspace/auth shell split completed
- [ ] Prototype pages migrated to Next.js destinations
- [ ] Feature modules extracted/refactored for maintainability
- [ ] Tests added/updated and passing
- [ ] Lint + type-check + full tests passing
- [ ] Manual validation completed on critical flows
- [ ] Prototype HTML dependency removed from runtime navigation

---

## NOTES

- Product-first consolidation decisions:
  - `dashboard.html` and `task_kanban.html` overlap in task visibility; dashboard should be summary, kanban should be operational board.
  - `execution_split_view.html` should enrich `/runs/[id]`, not become a standalone disconnected route.
  - `artifacts.html` should align with project-scoped artifact behavior already implemented at `/projects/[id]/artifacts`.
  - `index_welcome.html` concept (prompt-first entry) is useful but must not violate existing project-first context model; adopt as dashboard widget or controlled root entry, not separate static page parity.

- Architectural guardrails:
  - Keep API contracts in `frontend/src/lib/types.ts` as source of truth.
  - Prefer extending existing `features/*` modules over introducing cross-cutting mega-components.
  - Preserve URL stability for existing working routes to reduce migration risk.

- Confidence Score: **8.5/10** for one-pass implementation success (main uncertainty: backend availability for knowledge/tools/settings dynamic data endpoints).
