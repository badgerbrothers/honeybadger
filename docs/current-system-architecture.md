# Badgers MVP 当前系统架构设计（按代码实况）

## 1. 文档说明

本文只描述 **当前仓库里的实际实现**，不以 PRD、README 或其他设计文档中的理想态为准。

配套文档：

- 现状文档：`docs/current-system-architecture.md`
- 差距文档：`docs/target-architecture-gap-analysis.md`

- 代码基线：`master` 分支当前工作区
- 覆盖范围：`frontend/`、`backend/`、`worker/`、`docker-compose.yml`
- 目标：
  - 说明当前系统如何分层
  - 说明当前设计已经具备的优点
  - 给出每一块功能的实际调用链
  - 明确哪些链路已经打通，哪些只是“有代码但未真正闭环”

---

## 2. 当前总体架构

当前项目是一个单仓模块化系统，实际分为 4 个层次：

1. **Frontend（Next.js）**
   - 提供 Web UI 壳层
   - 当前真正落地的页面只有 `/` 和 `/projects`
   - 已有部分任务运行查看组件，但尚未挂到页面路由上

2. **Backend（FastAPI）**
   - 提供 HTTP API 和 WebSocket 接口
   - 管理核心资源：Project、Conversation、Task、TaskRun、Artifact、Memory
   - 负责数据库读写、对象存储调用、少量 AI 调用（MemoryService）

3. **Worker（独立 Python 进程）**
   - 轮询数据库中的 `task_runs`
   - 为任务创建 Docker Sandbox
   - 调用 Agent、模型层、工具层、技能层

4. **Infrastructure**
   - PostgreSQL：结构化数据
   - MinIO：文件/Artifact 对象存储
   - Docker：Sandbox 容器
   - Redis：在当前真实执行链中**尚未接入**

### 2.1 实际部署形态

当前 `docker-compose.yml` 只启动基础设施服务：

- `postgres`
- `redis`
- `minio`

它 **没有** 启动：

- FastAPI backend
- worker
- Next.js frontend

因此当前项目的真实运行方式是：

1. 先用 `docker-compose.yml` 启动基础设施
2. 再手动启动 `backend`
3. 再手动启动 `worker`
4. 再手动启动 `frontend`

### 2.2 当前真实架构图

```text
Browser
  -> Next.js frontend
     -> HTTP fetch -> FastAPI backend
     -> WebSocket  -> FastAPI backend event broadcaster

FastAPI backend
  -> PostgreSQL
  -> MinIO
  -> OpenAI (仅 memory_service)

Worker
  -> PostgreSQL（轮询 task_runs）
  -> Docker Sandbox
  -> 模型层 / 技能层 / 工具层

当前未接入主执行链：
  -> Redis（已声明，但 worker 主循环未使用）
  -> 后端 RAG API 的 index/search（当前是 TODO stub）
  -> Worker 到 WebSocket 的执行事件广播
```

---

## 3. 目录与模块分工

## 3.1 Frontend

`frontend/src/` 当前实际职责如下：

- `app/`
  - `page.tsx`：根路径直接跳转到 `/projects`
  - `projects/page.tsx`：当前唯一业务页面，显示项目列表和创建表单
  - `layout.tsx`：挂载 Header 和 React Query Provider
- `components/`
  - 通用 UI 组件和布局组件
- `features/projects/`
  - 已实际用于 `/projects` 页面
  - 覆盖：项目查询、项目创建、项目文件上传/删除相关组件与 hook
- `features/tasks/`
  - 已有任务运行查看组件、WebSocket hook、状态 badge
  - 当前没有页面路由接入
- `lib/`
  - API 请求封装
  - React Query client
  - WebSocket client

### 3.1.1 前端当前真实状态

- 已接通：
  - 项目列表
  - 项目创建
- 可复用但当前页面未接通：
  - 项目文件上传组件
  - 项目文件列表组件
  - TaskRun 实时查看组件
- 明显缺口：
  - `ProjectCard` 链接到 `/projects/{id}`，但该页面并不存在
  - Conversation / Task / Artifact / Memory 没有前端页面

## 3.2 Backend

`backend/app/` 当前实际职责如下：

- `main.py`
  - 创建 FastAPI 应用
  - 注册 CORS
  - 挂载所有 router
- `database.py`
  - 创建 async SQLAlchemy engine / session
  - 提供 `get_db`
  - 提供 `init_db`
- `models/`
  - SQLAlchemy 数据模型
- `schemas/`
  - Pydantic 请求/响应模型
- `routers/`
  - `projects.py`
  - `conversations.py`
  - `tasks.py`
  - `runs.py`
  - `artifacts.py`
  - `memory.py`
  - `rag.py`
- `services/`
  - `storage.py`：MinIO
  - `event_broadcaster.py`：WebSocket 连接管理
  - `memory_service.py`：摘要和向量生成

## 3.3 Worker

`worker/` 当前实际职责如下：

- `main.py`
  - 轮询 `task_runs` 表中 `pending` 状态任务
  - 将其改为 `running`
  - 创建 sandbox
  - 初始化模型、技能、工具、Agent
  - 执行任务并更新 `TaskRun`
- `orchestrator/agent.py`
  - 负责推理-工具调用-观察循环
- `sandbox/`
  - `manager.py`：高层 sandbox 生命周期
  - `docker_backend.py`：Docker SDK 封装
- `models/`
  - 当前存在两套模型抽象：
    - 一套是 `generate/stream` 风格
    - 一套是 `chat_completion + tool_calls` 风格
- `tools/`
  - 当前也存在两套工具接口风格
- `skills/`
  - 从 Markdown `SKILL.md` 动态加载技能
- `rag/`
  - 与 backend 下的 RAG 实现高度重复

---

## 4. 当前核心数据模型

## 4.1 业务主资源

| 资源 | 模型文件 | 当前职责 |
|---|---|---|
| Project | `backend/app/models/project.py` | 项目空间 |
| ProjectNode | `backend/app/models/project.py` | 项目内文件节点 |
| Conversation | `backend/app/models/conversation.py` | 对话容器 |
| Message | `backend/app/models/conversation.py` | 对话消息 |
| Task | `backend/app/models/task.py` | 逻辑任务定义 |
| TaskRun | `backend/app/models/task.py` | 单次执行实例 |
| SandboxSession | `backend/app/models/sandbox.py` | TaskRun 对应的 sandbox 记录 |
| Artifact | `backend/app/models/artifact.py` | 持久化输出文件 |
| ConversationSummary | `backend/app/models/memory.py` | 对话摘要 |
| ProjectMemory | `backend/app/models/memory.py` | 项目级语义记忆 |
| DocumentChunk | `backend/app/models/document_chunk.py` | RAG 文档分块 |

## 4.2 当前模型边界的优点

当前模型设计里，下面几处分层是比较清晰的：

1. **Task 与 TaskRun 分离**
   - `Task` 保存目标、技能、模型
   - `TaskRun` 保存状态、开始时间、完成时间、错误信息、运行期日志

2. **Artifact 与 ProjectNode 分离**
   - `ProjectNode` 更像项目目录里的正式文件记录
   - `Artifact` 更像执行产出物记录

3. **SandboxSession 独立建模**
   - 将运行状态与容器实例分离
   - 便于记录资源限制和终止时间

## 4.3 当前模型层的真实限制

1. `Task.current_run_id` 字段存在，但当前代码没有在创建 Run 或执行完成时维护它。
2. `DocumentChunk.project_id` 是 `str`，而其他主资源基本使用 `UUID`，这会让 RAG 层与主业务模型存在类型边界不一致。
3. Conversation/Task/Artifact 之间已建好关系，但很多关系还没有形成完整的端到端流程。

---

## 5. 当前架构设计的实际优点

以下优点是 **按当前代码现状** 成立的，不依赖 PRD 的未来设计。

## 5.1 仓库结构清晰

前端、后端、worker、基础设施被清楚拆开，便于分别演进：

- 前端专注页面和交互
- 后端专注资源管理和存储
- worker 专注执行
- 基础设施专注依赖服务

## 5.2 API 与数据模型对应关系比较直接

大部分 router 都能直接对应到一个核心资源：

- `/api/projects`
- `/api/conversations`
- `/api/tasks`
- `/api/runs`
- `/api/artifacts`
- `/api/projects/{project_id}/memories`

这种设计的优点是：

- 读代码时很容易定位资源入口
- 测试用例能按资源维度拆分
- 后续扩展权限、审计、中间件比较方便

## 5.3 后端和 worker 都使用异步 I/O

当前 backend 和 worker 都基于 async SQLAlchemy，会让：

- 数据库访问模型一致
- API 层和 worker 层的会话管理方式接近
- 后续补充长连接、事件流、外部服务调用时不必整体重构同步/异步模型

## 5.4 技能系统从代码中外置出来了

技能由 `worker/skills/*/SKILL.md` 定义，再由 `worker/skills/registry.py` 动态加载。

这个设计的实际好处是：

- 技能内容调整不必改 agent 主循环
- 技能可以以目录为边界独立维护
- 后续很容易补充更多技能模板

## 5.5 Sandbox 生命周期独立封装

即使当前执行链还没完全闭环，sandbox 的生命周期职责已经被分为：

- `SandboxManager`：高层编排
- `DockerBackend`：底层 Docker API 适配

这使得容器创建/启动/停止/删除逻辑不会散落在 worker 主循环中。

## 5.6 已有较完整的资源级测试布局

当前仓库已有分层测试：

- backend API tests
- backend schema / rag / memory tests
- worker agent / model / sandbox / tool tests

说明当前项目在结构上已经为回归验证留出了位置。

---

## 6. 实际调用链

本节只写当前代码真实存在的调用链。

## 6.1 前端应用启动链

### 6.1.1 根路径进入链

1. 浏览器请求 `/`
2. `frontend/src/app/page.tsx`
3. 直接 `redirect('/projects')`
4. 进入 `frontend/src/app/projects/page.tsx`

### 6.1.2 全局布局链

1. `frontend/src/app/layout.tsx`
2. 挂载 `QueryClientProvider`
3. 挂载 `Header`
4. 在 `<main>` 中渲染具体页面

---

## 6.2 项目列表调用链

这是当前前端里最完整、真实打通的一条主链路。

1. `frontend/src/app/projects/page.tsx`
2. 渲染 `ProjectList`
3. `frontend/src/features/projects/components/ProjectList.tsx`
4. 调用 `useProjects`
5. `frontend/src/features/projects/hooks/useProjects.ts`
6. 调用 `fetchProjects`
7. `frontend/src/features/projects/api/projects.ts`
8. 调用 `request('/projects')`
9. `frontend/src/lib/api.ts`
10. 发起 `GET http://localhost:8000/api/projects`
11. `backend/app/routers/projects.py:list_projects`
12. `SELECT Project`
13. 返回 `ProjectResponse[]`
14. React Query 缓存结果
15. `ProjectList` 渲染卡片

---

## 6.3 项目创建调用链

1. `frontend/src/app/projects/page.tsx`
2. 渲染 `CreateProjectForm`
3. `frontend/src/features/projects/components/CreateProjectForm.tsx`
4. 本地校验 `name` / `description`
5. 调用 `useCreateProject`
6. `frontend/src/features/projects/hooks/useCreateProject.ts`
7. 调用 `createProject`
8. `frontend/src/features/projects/api/projects.ts`
9. 调用 `request('/projects', { method: 'POST' })`
10. `frontend/src/lib/api.ts`
11. 发起 `POST /api/projects`
12. `backend/app/routers/projects.py:create_project`
13. 构造 `Project(**project.model_dump())`
14. `db.add` -> `db.commit` -> `db.refresh`
15. 返回 `ProjectResponse`
16. 前端 `invalidateQueries(['projects'])`
17. 项目列表重新拉取

---

## 6.4 项目文件上传调用链

这条链路的 **后端和前端组件都存在**，但当前页面未挂载。

1. 某页面若渲染 `FileUploadZone`
2. `frontend/src/features/projects/components/FileUploadZone.tsx`
3. 本地校验：
   - 扩展名
   - 50MB 大小上限
4. 调用 `useUploadFile(projectId)`
5. `frontend/src/features/projects/hooks/useUploadFile.ts`
6. 调用 `uploadProjectFile(projectId, file)`
7. `frontend/src/features/projects/api/files.ts`
8. 直接用 `fetch` 提交 `multipart/form-data`
9. 请求 `POST /api/projects/{project_id}/files/upload`
10. `backend/app/routers/projects.py:upload_project_file`
11. 检查项目是否存在
12. 校验扩展名和大小
13. 构造 `ProjectNode`
14. 调用 `storage_service.upload_file(...)`
15. `backend/app/services/storage.py`
16. 通过 MinIO SDK 写入对象存储
17. `db.commit()` 持久化 `ProjectNode`
18. 返回 `ProjectFileUploadResponse`
19. 前端 `invalidateQueries(['projectFiles', projectId])`

### 当前真实边界

- 当前上传链 **不会** 触发 RAG 索引
- 当前上传链只做了：
  - 数据库存 `ProjectNode`
  - 对象存储写入文件

---

## 6.5 项目文件列表调用链

这条链路的前端组件已存在，但当前页面未挂载。

1. 某页面渲染 `FileList(projectId)`
2. `frontend/src/features/projects/components/FileList.tsx`
3. 调用 `useProjectFiles(projectId)`
4. `frontend/src/features/projects/hooks/useProjectFiles.ts`
5. 调用 `fetchProjectFiles(projectId)`
6. `frontend/src/features/projects/api/files.ts`
7. 发起 `GET /api/projects/{project_id}/files`
8. `backend/app/routers/projects.py:list_project_files`
9. 查询 `ProjectNode where project_id = ? and node_type = FILE`
10. 返回文件列表

### 删除调用链

1. `FileList` 中点击 Delete
2. 调用 `deleteProjectFile(projectId, fileId)`
3. 发起 `DELETE /api/projects/{project_id}/files/{file_id}`
4. `backend/app/routers/projects.py:delete_project_file`
5. 先删除数据库记录
6. 再尝试调用 `storage_service.delete_file(storage_path)`
7. 前端刷新 `projectFiles` 查询

---

## 6.6 Conversation 调用链

当前 Conversation 只有后端 API，前端没有页面接入。

### 6.6.1 创建 Conversation

1. 客户端 `POST /api/conversations`
2. `backend/app/routers/conversations.py:create_conversation`
3. 构造 `Conversation(**conversation.model_dump())`
4. `db.add` -> `db.commit` -> `db.refresh`
5. 返回 `ConversationResponse`

### 6.6.2 查询 Conversation 列表

1. `GET /api/conversations`
2. 可选 `project_id`
3. `backend/app/routers/conversations.py:list_conversations`
4. 查询 `Conversation`
5. 返回数组

### 6.6.3 创建 Message

1. `POST /api/conversations/{conversation_id}/messages`
2. `backend/app/routers/conversations.py:create_message`
3. 先检查 Conversation 是否存在
4. 构造 `Message(conversation_id=..., **message.model_dump())`
5. `db.add` -> `db.commit` -> `db.refresh`
6. 返回 `MessageResponse`

### 当前真实边界

- `POST /api/conversations/{id}/messages` **不会自动创建 Task**
- 这与旧文档中的“发消息就创建任务”描述不同

---

## 6.7 Task 调用链

当前 Task 主要由后端 API 提供，前端尚未接入。

### 6.7.1 创建 Task

1. `POST /api/tasks`
2. `backend/app/routers/tasks.py:create_task`
3. 构造 `Task(**task.model_dump())`
4. `db.add` -> `db.commit` -> `db.refresh`
5. 返回 `TaskResponse`

### 6.7.2 查询 / 更新 / 删除 Task

1. `GET /api/tasks`
2. `GET /api/tasks/{task_id}`
3. `PATCH /api/tasks/{task_id}`
4. `DELETE /api/tasks/{task_id}`
5. 均由 `backend/app/routers/tasks.py` 直接操作 `Task` 表

### 当前真实边界

- `Task` 只是逻辑定义
- 创建 Task 时 **不会自动生成 Run**
- 当前也 **不会** 推送到 Redis

---

## 6.8 TaskRun 创建与列表调用链

### 6.8.1 创建 TaskRun

1. `POST /api/tasks/{task_id}/runs`
2. `backend/app/routers/tasks.py:create_task_run`
3. 检查 Task 是否存在
4. 构造 `TaskRun(task_id=task_id, status=PENDING)`
5. `db.add` -> `db.commit` -> `db.refresh`
6. 返回 `TaskRunResponse`

### 6.8.2 查询 Task 的全部 Runs

1. `GET /api/tasks/{task_id}/runs`
2. `backend/app/routers/tasks.py:list_task_runs`
3. 检查 Task 是否存在
4. 查询 `TaskRun where task_id = ?`
5. 返回数组

### 当前真实边界

- 创建 Run 时：
  - **不会** 维护 `Task.current_run_id`
  - **不会** 发 Redis 消息
  - **不会** 立即向前端广播事件

---

## 6.9 Run 查询 / 取消 / WebSocket 调用链

### 6.9.1 查询单个 Run

1. `GET /api/runs/{run_id}`
2. `backend/app/routers/runs.py:get_run`
3. 查询 `TaskRun`
4. 返回 `TaskRunResponse`

### 6.9.2 取消 Run

1. `POST /api/runs/{run_id}/cancel`
2. `backend/app/routers/runs.py:cancel_run`
3. 检查 Run 是否存在
4. 检查状态必须是 `pending` 或 `running`
5. 更新为 `cancelled`
6. 写入 `completed_at`
7. `db.commit()` / `db.refresh()`
8. 调用 `broadcaster.broadcast(run_id, {"type": "status_change", "status": "cancelled"})`
9. 返回更新后的 `TaskRunResponse`

### 6.9.3 WebSocket 流

1. 前端 `useTaskRunStream(runId)`
2. `frontend/src/features/tasks/hooks/useTaskRunStream.ts`
3. 构造 `ws://localhost:8000/api/runs/{run_id}/stream`
4. `frontend/src/lib/websocket.ts`
5. 创建浏览器 WebSocket
6. `backend/app/routers/runs.py:stream_events`
7. `event_broadcaster.connect(run_id, websocket)`
8. 等待 `receive_text()`
9. 若有后端广播，则将事件发给连接

### 当前真实边界

- 当前 backend 里真正会广播到这个流的只有：
  - `cancel_run`
- worker 主循环 **没有** 对 `event_broadcaster` 发执行事件
- 因此前端 `TaskRunViewer` 当前拿不到真实执行步骤、工具调用、Artifact 创建事件

---

## 6.10 Artifact 调用链

当前 Artifact 只有后端 API，前端没有页面接入。

### 6.10.1 上传 Artifact

1. `POST /api/artifacts/upload?project_id=...&task_run_id=...`
2. `backend/app/routers/artifacts.py:upload_artifact`
3. 读取上传文件内容
4. 检查 100MB 大小限制
5. 调用 `storage_service.upload_file(object_name, content, content_type)`
6. 写入 `Artifact` 记录
7. `db.commit()` / `db.refresh()`
8. 返回 `ArtifactResponse`

### 6.10.2 获取 Artifact 元数据

1. `GET /api/artifacts/{artifact_id}`
2. 查询 `Artifact`
3. 返回元数据

### 6.10.3 下载 Artifact

1. `GET /api/artifacts/{artifact_id}/download`
2. 查询 `Artifact`
3. 调用 `storage_service.download_file(storage_path)`
4. 用 `StreamingResponse` 返回文件流

### 6.10.4 删除 Artifact

1. `DELETE /api/artifacts/{artifact_id}`
2. 先删数据库记录
3. 再删 MinIO 对象

### 当前真实边界

- 当前没有 “save to project” API
- 当前 worker 主流程也没有自动创建 Artifact

---

## 6.11 Memory 调用链

Memory API 已有后端实现，但前端没有页面。

### 6.11.1 生成 Conversation Summary

1. `POST /api/conversations/{conversation_id}/summarize`
2. `backend/app/routers/memory.py:summarize_conversation`
3. 查询 Conversation
4. 查询该 Conversation 的全部 Message
5. 调用 `memory_service.summarize_conversation(messages)`
6. `backend/app/services/memory_service.py`
7. 通过 `AsyncOpenAI().chat.completions.create(...)` 生成摘要
8. 写入 `ConversationSummary`
9. 返回结果

### 6.11.2 获取最新 Summary

1. `GET /api/conversations/{conversation_id}/summary`
2. 查询 `ConversationSummary`
3. 按 `created_at desc` 取第一条
4. 返回结果

### 6.11.3 创建 ProjectMemory

1. `POST /api/projects/{project_id}/memories`
2. `backend/app/routers/memory.py:create_project_memory`
3. 检查 Project 是否存在
4. 调用 `memory_service.generate_embedding(content)`
5. 通过 OpenAI Embeddings 生成向量
6. 写入 `ProjectMemory`
7. 返回结果

### 6.11.4 搜索 ProjectMemory

1. `POST /api/projects/{project_id}/memories/search`
2. `backend/app/routers/memory.py:search_project_memories`
3. 调用 `memory_service.search_memories(project_id, query, limit, db)`
4. 使用 `ProjectMemory.embedding.cosine_distance(...)` 做向量搜索
5. 返回匹配结果

---

## 6.12 RAG API 调用链

当前 RAG 只有一半是真的。

### 6.12.1 已实现的部分

#### 查询 Chunk 列表

1. `GET /api/projects/{project_id}/chunks`
2. `backend/app/routers/rag.py:list_chunks`
3. 查询 `DocumentChunk`
4. 返回精简列表

#### 删除 Chunk

1. `DELETE /api/projects/{project_id}/chunks/{chunk_id}`
2. `backend/app/routers/rag.py:delete_chunk`
3. 查询单个 `DocumentChunk`
4. 删除并提交

### 6.12.2 尚未实现的部分

#### Index API

1. `POST /api/projects/{project_id}/documents/index`
2. `backend/app/routers/rag.py:index_document`
3. 当前直接返回 `"Indexing not yet implemented"`

#### Search API

1. `POST /api/projects/{project_id}/search`
2. `backend/app/routers/rag.py:search_chunks`
3. 当前直接返回空数组

### 当前真实边界

- backend 下和 worker 下都各有一套 `rag/indexer.py`、`rag/retriever.py`
- 但后端公开 API 的 index/search 并未接到这些实现上
- 项目文件上传也未触发 RAG 索引

---

## 6.13 Worker 主循环调用链

这是当前后端之外最重要的一条内部链路。

1. 启动 `worker/main.py`
2. `main()` 调用：
   - `configure_logging()`
   - `setup_signal_handlers()`
   - `worker_loop()`
3. `worker_loop()` 持续循环
4. 为每轮循环创建 `AsyncSession`
5. 调用 `get_next_pending_task(session)`
6. 在 `backend.app.models.task.TaskRun` 中查询最早的 `PENDING`
7. 如果找到：
   - 将其改为 `RUNNING`
   - 写入 `started_at`
   - `session.commit()`
8. 调用 `execute_task_run(task_run.id, session)`

### 6.13.1 execute_task_run 内部链

1. 重新查询 `TaskRun`
2. 查询其关联 `Task`
3. 构造 `SandboxManager`
4. `sandbox.create()`
5. `worker/sandbox/manager.py`
6. `DockerBackend.create_container(...)`
7. `DockerBackend.start_container(...)`
8. 创建 `SandboxSession` 数据库记录
9. 调用 `create_model_provider(...)`
10. 如果 `task.skill` 存在，则调用 `get_skill(task.skill)`
11. 调用 `get_all_tools(sandbox)`
12. 创建 `Agent`
13. `agent.run(goal=task.goal, system_prompt=...)`
14. 成功则把 `TaskRun.status` 改成 `COMPLETED`
15. 失败则把 `TaskRun.status` 改成 `FAILED`
16. 无论成功失败，最后都尝试 `sandbox.destroy()`
17. 更新 `SandboxSession.terminated_at`

### 当前真实边界

- worker 当前是 **轮询数据库**，不是消费 Redis 队列
- 这意味着真实执行链是：
  - API 写入 `task_runs`
  - worker 轮询 `task_runs`
  - worker 抢占 `pending` 任务

---

## 6.14 Agent 推理循环调用链

`worker/orchestrator/agent.py` 当前设计目标是一个典型的推理-动作循环。

### 6.14.1 理想上的当前代码流程

1. `Agent.run(goal, system_prompt)`
2. 初始化 `messages`
   - 可选 system
   - 必有 user(goal)
3. 根据模型类型构造工具 schema
4. 循环直到 `max_iterations`
5. 调用 `model.chat_completion(messages, tools, temperature)`
6. 如果返回 `tool_calls`
   - 记录 assistant message
   - 对每个 tool call 执行 `_execute_tool(tool_name, arguments)`
   - 将工具结果追加成下一轮 message
7. 如果 `finish_reason == "stop"`
   - 返回模型文本结果

### 6.14.2 当前真实未闭环点

当前 Agent 循环在代码结构上是成立的，但主链路存在两个关键接口未收口：

1. **模型接口双轨**
   - `worker/main.py` 用的是 `models.factory.create_model_provider()`
   - 这个 factory 返回的是：
     - `models.openai_provider.OpenAIProvider`
     - `models.anthropic_provider.AnthropicProvider`
   - 这套接口提供的是：
     - `generate()`
     - `stream()`
   - 但 `Agent` 依赖的是：
     - `chat_completion()`
     - `tool_calls`
   - 仓库中虽然还有：
     - `models.openai_compat.py`
     - `models.anthropic_native.py`
   - 它们才实现了 `chat_completion()` 协议，但 **当前没有接入 factory**

2. **工具接口双轨**
   - `Agent` 期望工具实现 `tools.tool_base.Tool`
   - 但 `get_all_tools()` 实际返回的是：
     - `BrowserTool`
     - `WebFetchTool`
     - `PythonTool`
   - 这三个类继承的是 `BaseTool`
   - `BaseTool` 的 `execute(self, params: Dict[str, Any])`
   - 而 `Agent` 调用的是 `tool.execute(**arguments)`
   - 两边协议并不一致

### 结论

Worker 主循环、Agent、模型层、工具层已经具备“拼成执行系统”的模块形态，但当前代码里这些模块 **尚未在接口层完全接通**。

---

## 6.15 当前工具层调用链

## 6.15.1 BrowserTool

当前 `worker/tools/browser.py` 的真实行为：

1. 在 worker 进程中启动 Playwright
2. 创建本地 browser/context/page
3. 支持：
   - `open`
   - `click`
   - `type`
   - `extract`
   - `screenshot`

### 当前真实边界

- 它当前不是通过 sandbox 执行
- 它实际运行位置是 **worker 本机进程**

## 6.15.2 WebFetchTool

当前 `worker/tools/web.py` 的真实行为：

1. 在 worker 进程内创建 `httpx.AsyncClient`
2. 发起 GET / POST
3. 返回：
   - status_code
   - body
   - json
   - headers

### 当前真实边界

- 它当前不是通过 sandbox 执行
- 它实际运行位置也是 **worker 本机进程**

## 6.15.3 PythonTool

当前 `worker/tools/python.py` 的真实行为：

1. 接收 Python 代码
2. Base64 编码
3. 通过 `sandbox.execute(command)` 在容器中运行
4. 返回 stdout/stderr/exit_code/execution_time

### 当前真实边界

- 这是当前工具集中 **唯一明确通过 sandbox 执行** 的工具

## 6.15.4 FileTool

`worker/tools/file.py` 中存在：

- `FileListTool`
- `FileReadTool`
- `FileWriteTool`

### 当前真实边界

- 这些工具 **没有** 被 `get_all_tools()` 注册
- 因此当前 worker 主循环中默认拿不到文件工具

---

## 7. 当前真实系统边界与未闭环点

为了让本文严格符合代码现状，下面明确列出关键未闭环点。

## 7.1 Redis 已声明但未接入任务执行链

- `docker-compose.yml` 启动了 Redis
- README 也提到任务队列
- 但 `worker/main.py` 当前实际是数据库轮询，不是 Redis 消费

## 7.2 WebSocket 实时执行链未打通

- 前端有 `TaskRunViewer` 和 `useTaskRunStream`
- 后端有 `EventBroadcaster`
- 但 worker 执行过程中没有调用 broadcaster 推送步骤、工具调用、Artifact 事件
- 当前真正会推送的只有取消事件

## 7.3 RAG 公共 API 只有外壳

- `backend/app/routers/rag.py` 的 `index_document` 和 `search_chunks` 仍是 stub
- 项目文件上传不会自动索引
- 因此 RAG 模块当前更像“库代码已在，业务链路未接入”

## 7.4 Worker 存在模型协议双轨

- `generate/stream` 一套
- `chat_completion/tool_calls` 一套
- 当前主流程使用的是前者，Agent 依赖的是后者

## 7.5 Worker 存在工具协议双轨

- `tools.tool_base.Tool` 一套
- `tools.base.BaseTool` 一套
- 当前 `get_all_tools()` 走的是后者，Agent 依赖的是前者

## 7.6 前端业务页面覆盖度仍然有限

- 真实可访问页面只有 `/projects`
- 项目详情页缺失
- Conversation / Task / Artifact / Memory 没有可用页面

## 7.7 配置命名还未完全统一

当前仓库中，配置文档与真实代码读取的环境变量命名存在偏差，例如：

- backend `config.py` 读取的是 `minio_*`
- `.env.example` 主要提供的是 `S3_*`

这说明配置层仍有整理空间。

---

## 8. 建议如何阅读当前代码

如果要按真实链路继续开发，推荐从下面顺序切入：

1. `frontend/src/app/projects/page.tsx`
2. `frontend/src/features/projects/*`
3. `frontend/src/lib/api.ts`
4. `backend/app/main.py`
5. `backend/app/routers/projects.py`
6. `backend/app/models/*`
7. `worker/main.py`
8. `worker/orchestrator/agent.py`
9. `worker/models/*`
10. `worker/tools/*`

这个顺序能最快看清：

- 当前已打通的 UI/API 链
- 当前任务执行链的真实入口
- 当前 worker 接口层为什么还没有完全闭环

---

## 9. 一句话总结

当前 Badgers MVP 的代码库已经具备了 **前端壳层 + 后端资源管理 + worker 执行框架 + sandbox + storage + memory + 技能系统** 的完整骨架；其中 **项目管理链路已基本打通**，而 **任务执行、实时事件、RAG、Artifact 自动产出** 仍处于“模块已存在、接口尚未完全收口”的阶段。
