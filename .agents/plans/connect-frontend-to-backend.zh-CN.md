# 功能：前端对接后端（认证 + 工作区 + 运行 + RAG）

下面这份计划应当是完整的，但在开始实现前，你必须先校验文档、代码库模式以及任务合理性。

请特别注意已有工具函数、类型、模型的命名，并从正确文件中导入。

## 功能说明

将现有 Next.js 前端（当前由 `WorkspaceContext` / `RagContext` 的本地 mock 状态驱动）接入已运行的微服务基线（`nginx/` 后面的 `services/*`）。

目标结果：用户可以注册/登录、创建/选择项目与会话、发送消息创建任务与运行、通过 WebSocket 查看运行事件，并管理 RAG 集合与文件上传。

## 用户故事

作为一个已登录用户，  
我希望通过 Web UI 创建项目/会话、执行任务、管理 RAG 知识，  
从而可以端到端跑通 Badgers MVP 流程，而不依赖 mock 数据。

## 问题陈述

前端页面已存在，但依赖内存种子数据（`WorkspaceContext.tsx`、`RagContext.tsx`）和伪认证（`AuthPage.tsx` 的表单提交到 `/dashboard`）。后端已提供认证 API 与实时运行流，但前端还没有 API 客户端、认证/Token 存储、数据缓存和 WebSocket 接线。

## 方案陈述

增加一层轻量前端平台能力：

- `AuthProvider`：通过 auth-service 端点管理 access/refresh token，并暴露当前用户。
- `ApiClient`：`fetch` 封装，注入 bearer token，401 自动刷新，并统一错误格式。
- `QueryClientProvider`：使用 TanStack React Query 缓存服务端状态。
- `RunStream`：连接 `WS /api/runs/{run_id}/stream?token=...` 并实时更新 UI。

然后重构现有 UI 上下文/页面，改为调用后端 API：

- Workspace：通过 project-service + task-service 获取项目/会话/消息/任务。
- Dashboard：通过 task-service 的 queue-status 与 kanban 端点获取任务看板。
- RAG：通过 rag-service 管理集合/文件，通过 project-service 做项目绑定。
- Artifacts：按 run 列表展示并通过鉴权下载。

## 功能元信息

**功能类型**：增强 / 重构（UI + 集成）  
**预估复杂度**：高  
**主要影响系统**：`frontend/`（Next.js）、auth-service、project-service、task-service、rag-service（通过现有端点）  
**依赖**：

- 已有网关路由：`nginx/nginx.conf`
- 已有认证端点：`services/auth-service` controllers
- React Query 已在依赖中但未接线：`frontend/package.json`

---

## 上下文参考

### 相关代码文件（实现前必须阅读）

- `frontend/src/features/auth/AuthPage.tsx`（12-106 行）：伪认证表单，需替换为真实 `/api/auth/*` 调用。
- `frontend/src/features/workspace/WorkspaceContext.tsx`（11-200+ 行）：项目/会话/消息/任务 mock 种子状态，需替换为后端驱动。
- `frontend/src/app/(workspace)/conversation/page.tsx`（14-210+ 行）：当前调用 mock 的 `sendMessage()`，需改成异步流程：message -> task -> run。
- `frontend/src/app/(workspace)/dashboard/page.tsx`（12-200+ 行）：看板使用 `schedule|queue|inprogress|done`，后端是 `scheduled|queued|in_progress|done`。
- `services/auth-service/.../AuthController.java`：`/api/auth/register|login|refresh|logout`。
- `services/auth-service/.../UserController.java`：`/api/users/me`。
- `services/task-service/app/routers/tasks.py`（117-246+）：任务 CRUD、`GET /models`、`GET /kanban`、`PATCH /{task_id}/queue-status`、`POST /{task_id}/runs`。
- `services/task-service/app/routers/runs.py`（44-133）：`GET /runs/{id}`、`GET /runs/{id}/artifacts`、`POST /runs/{id}/cancel`、`WS /runs/{id}/stream`。
- `services/project-service/app/routers/projects.py`（41-220）：项目 + 项目文件上传 + 文件列表 + 产物列表。
- `services/project-service/app/routers/conversations.py`（34-143）：会话 + 消息 CRUD。
- `services/project-service/app/routers/project_rag.py`：项目与全局 RAG 绑定。
- `services/rag-service/app/routers/rag_collections.py`（50-214）：全局 RAG 集合 + 文件上传 + 文件列表。
- `docker-compose.yml`：前端环境变量 `NEXT_PUBLIC_API_URL=http://localhost/api` 与 `NEXT_PUBLIC_WS_URL=ws://localhost`。

### 需要新建的文件

- `frontend/src/app/providers.tsx`：组合 QueryClientProvider + AuthProvider。
- `frontend/src/lib/config.ts`：解析 `NEXT_PUBLIC_API_URL` 和 `NEXT_PUBLIC_WS_URL`，并给本地开发默认值。
- `frontend/src/lib/auth/AuthContext.tsx`：Token 存储 + `login/register/refresh/logout` + `useAuth`。
- `frontend/src/lib/api/client.ts`：带 401 自动刷新与类型辅助的 `apiFetch` 封装。
- `frontend/src/lib/api/types.ts`：与后端 schema 对齐的共享 DTO（Project/Conversation/Message/Task/TaskRun/Artifact/RagCollection/RagFile/ModelCatalog）。
- `frontend/src/lib/api/endpoints.ts`：各域具体 API 函数（projects/conversations/tasks/runs/artifacts/rags）。
- `frontend/src/lib/ws/runStream.ts`：run stream 的 WebSocket 辅助函数。
- `frontend/src/lib/download.ts`：使用鉴权 fetch + Blob 的下载辅助函数。
- `frontend/src/app/(workspace)/runs/[runId]/page.tsx`：运行详情页（状态、事件、产物）。

### 相关文档（实现前建议阅读）

- Next.js App Router 数据获取  
  https://nextjs.org/docs/app/building-your-application/data-fetching/fetching  
  原因：后端请求放在客户端组件并通过 API client 调用，避免服务端访问 localStorage token。
- TanStack Query（React）  
  https://tanstack.com/query/latest/docs/framework/react/overview  
  原因：服务端状态缓存与 mutation 后失效刷新标准方案。
- WebSocket API  
  https://developer.mozilla.org/en-US/docs/Web/API/WebSocket  
  原因：正确处理生命周期、清理与重连模式。

### 需遵循模式

- 后端鉴权模式：所有服务端点使用 FastAPI `HTTPBearer`，要求 `Authorization: Bearer <accessToken>`。
- 队列状态命名（后端）：`scheduled|queued|in_progress|done`。
- 运行流契约：WebSocket 需 `token` 查询参数，事件会广播并追加到 `TaskRun.logs`。

---

## 实施计划

### 阶段 1：基础层

增加前端 providers 与 API/认证层，让后续工作都基于统一基础能力。

任务：

- 在根布局加 `Providers`。
- 加 `AuthProvider` 与 token 存储。
- 加带 401 自动刷新的 `ApiClient` 封装。
- 加 `RunStream` helper。

### 阶段 2：核心实现

将当前页面/上下文改为后端 API 驱动，停止依赖内存 mock 状态。

任务：

- 替换 `AuthPage` 的伪认证。
- 重构 `WorkspaceContext` 为后端驱动状态（项目、会话、消息、任务）。
- 接通 `ConversationPage` 发送链路：创建消息 -> 创建任务 -> 创建运行 -> 跳转运行页。
- 接通 `DashboardPage` 到 `/api/tasks/kanban` 与 `/api/tasks/{id}/queue-status`。

### 阶段 3：集成

在 UI 中启用产物与 RAG 管理。

任务：

- 运行详情页：WebSocket + 产物列表 + 下载。
- `RagContext` 从 mock 替换为 `/api/rags` 与 `/api/rags/{id}/files`。
- 实现 RAG 文件上传与项目文件上传。
- 增加项目绑定活跃 RAG 的 UI（PUT `/api/projects/{id}/rag`）。

### 阶段 4：测试与验证

增加快速校验，确保前端正确性，并提供手工 e2e 清单。

任务：

- 前端 type-check 与 lint。
- 可选：针对 API client 错误/刷新处理加基础单测（vitest）。
- 基于 docker-compose 做手工流程验证。

---

## 分步任务（必须按顺序执行，每步可独立验证）

1. 创建 `frontend/src/lib/config.ts`  
   实现 `API_BASE_URL`、`WS_BASE_URL` 默认值（`http://localhost/api`、`ws://localhost`）。  
   验证：`cd frontend; npm run type-check`

2. 创建 `frontend/src/lib/auth/AuthContext.tsx`  
   实现 token 持久化、`login/register/refresh/logout`、`getAccessToken()`、`useAuth()`。  
   注意：运行环境 `JWT_SECRET` 至少 32 字节，否则 auth-service 启动失败。  
   验证：`cd frontend; npm run type-check`

3. 创建 `frontend/src/lib/api/client.ts`  
   实现 `apiFetch(...)`：拼接基地址、注入 Authorization、401 刷新后重试一次、解析 JSON/Blob、统一错误对象。  
   验证：`cd frontend; npm run type-check`

4. 创建 `frontend/src/app/providers.tsx` 并更新 `frontend/src/app/layout.tsx`  
   实现 QueryClientProvider + AuthProvider（可选全局错误边界）。  
   验证：`cd frontend; npm run build`

5. 更新 `frontend/src/features/auth/AuthPage.tsx`  
   把 `<form action="/dashboard">` 替换为受控表单 + `auth.login/register`。成功后跳转 `/conversation`。  
   验证：`cd frontend; npm run type-check`

6. 重构 `frontend/src/features/workspace/WorkspaceContext.tsx`  
   删除全部 seed/mock 和 `Math.random()` id。  
   新增 React Query 获取与 mutation：  
   projects：`/api/projects`  
   conversations：`/api/conversations?project_id=...`  
   messages：`/api/conversations/{id}/messages`  
   tasks：`/api/tasks?...` 或 `/api/tasks/kanban?...`  
   注意：后端 UUID 统一字符串化，`active*Id` 在 refetch 后保持稳定。  
   验证：`cd frontend; npm run type-check`

7. 更新 `frontend/src/app/(workspace)/conversation/page.tsx`  
   新增 `GET /api/tasks/models` 模型列表。  
   发送流程改为：  
   `POST /messages` -> `POST /tasks` -> `POST /tasks/{id}/runs` -> 跳转 `/runs/{run_id}`。  
   新增附件上传到 `POST /api/projects/{project_id}/files/upload`。  
   验证：`cd frontend; npm run type-check`

8. 更新 `frontend/src/app/(workspace)/dashboard/page.tsx`  
   看板数据改为 `GET /api/tasks/kanban?project_id=...`。  
   拖拽更新改为 `PATCH /api/tasks/{id}/queue-status?queue_status=...`。  
   注意：UI 状态与后端状态映射。  
   验证：`cd frontend; npm run type-check`

9. 创建 `frontend/src/app/(workspace)/runs/[runId]/page.tsx`  
   实现运行状态页：详情、WebSocket 事件追加、产物列表、产物下载、取消运行。  
   验证：`cd frontend; npm run build`

10. 重构 `frontend/src/features/rag/RagContext.tsx` 并更新 RAG 页面  
    删除 seed/mock。  
    新增 React Query：RAG 集合 CRUD、RAG 文件列表/上传。  
    新增项目绑定 UI：`/api/projects/{project_id}/rag`。  
    验证：`cd frontend; npm run type-check`

---

## 测试策略

### 单元测试

- 使用 mocked fetch，为 `apiFetch` 的 401 刷新逻辑添加小型 vitest 测试。

### 集成测试

- 通过 docker compose 手工验证（该仓库架构下信号最快）。

### 边界场景

- access token 过期时应自动 refresh 并重试原请求。
- refresh 返回 401 时应登出并跳转 `/login`。
- WebSocket token 无效返回 4401 时，UI 显示“session expired”并提示重新登录。
- 文件上传大小/类型错误要展示可读错误信息。

---

## 验证命令

### Level 1：语法与风格

- `cd frontend; npm run lint`
- `cd frontend; npm run type-check`

### Level 2：单元测试

- `cd frontend; npm test`

### Level 3：集成测试

- （可选，后端）`cd backend; uv run pytest -q`（legacy）

### Level 4：手工验证

1. `docker compose up --build -d`
2. 打开 `http://localhost:3000`
3. 注册并登录
4. 创建项目和会话
5. 发送消息 -> 创建任务 -> 创建运行 -> 跳转运行页
6. 观察 WebSocket 实时事件
7. 确认产物出现且可下载
8. 创建 RAG 集合、上传文件、绑定到项目、上传项目文件触发索引任务

---

## 验收标准

- [ ] 认证 UI 使用真实后端端点并持久化 JWT
- [ ] 所有鉴权 API 调用携带 bearer token 且 401 自动刷新
- [ ] 项目/会话/消息由后端加载，变更可立即反映在 UI
- [ ] 发送消息会创建 task + run 并跳转到运行页面
- [ ] 运行页面显示 WebSocket 实时事件并列出产物
- [ ] Dashboard 反映后端 kanban 并支持 queue-status 更新
- [ ] RAG 页面通过 rag-service 管理集合和文件上传
- [ ] `npm run lint`、`npm run type-check`、`npm test` 通过

---

## 完成检查清单

- [ ] 所有任务按顺序完成
- [ ] 每个任务完成后立即通过对应验证
- [ ] 所有验证命令执行成功
- [ ] 基于 compose 的手工端到端流程验证通过

---

## 备注

- 当前前端没有 API hooks；集成需要新增 `lib/` 层并接入 providers。
- `frontend/src/app/rag/rag.css` 和 `frontend/src/features/rag/RagSidebar.tsx` 已有未暂存改动；RAG 工作应在其基础上叠加，不要覆盖。

**信心评分**：7/10（重构面较大，但后端端点与路由已就绪）
