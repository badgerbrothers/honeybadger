# Feature: Global RAG Registry And Chat Selection

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

实现“全局可复用 RAG”能力：用户可以先创建多个 RAG（知识库集合），再在不同 Project 中选择一个 RAG 使用，而不是每个 Project 绑定独立文档库。  
同时升级当前单页 Chat 交互：输入区新增 `RAG` 选择、`Model` 选择、附件上传，并在输入框上方显示已选文件。

## User Story

As a technical user managing multiple AI workspaces  
I want to create reusable global RAG collections and assign one collection to each project  
So that I can reuse the same knowledge base across projects without duplicated uploads/indexing.

## Problem Statement

当前系统是 project-centric RAG：

- `DocumentChunk` 以 `project_id` 为主过滤键（`services/rag-service/app/models/document_chunk.py:23`）
- 检索入口按 project 维度检索（`services/rag-service/app/services/rag_service.py:72,127`）
- 上传文件后直接按 project 调度索引（`services/project-service/app/routers/projects.py:66,114`）
- Worker 检索上下文时仅传 `task.project_id`（`worker/main.py:181,198`，`worker/rag/retriever.py`）

这导致：

1. 同一知识库无法跨项目复用（重复上传与索引）
2. Chat 前端无法真正选择“某个全局 RAG”
3. UI 的 RAG 选择目前只能退化为项目文件选择，不符合需求

## Solution Statement

引入 `RAG Collection` 作为全局一级资源，并将 “Project -> active_rag_collection_id” 作为绑定关系。  
RAG 索引/检索改为优先按 `rag_collection_id`，兼容旧 `project_id` 过渡。  
Chat 页面增加真实 RAG/Model 选择和附件上传，附件上传到“当前选中 RAG”而非项目文件目录。

## Feature Metadata

**Feature Type**: New Capability + Enhancement  
**Estimated Complexity**: High  
**Primary Systems Affected**:

- `services/rag-service`
- `services/project-service`
- `services/task-service`
- `worker`
- `frontend/src/features/welcome`
- `backend/alembic`

**Dependencies**:

- FastAPI + SQLAlchemy async
- PostgreSQL + pgvector
- RabbitMQ queue publish/consume
- Next.js 14 App Router

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `services/rag-service/app/models/document_chunk.py` (lines 10-30) - Why: 当前 chunk 按 `project_id` 绑定，需扩展为支持 `rag_collection_id`
- `services/rag-service/app/models/document_index_job.py` (lines 23-36) - Why: 索引任务模型当前同样按 `project_id/project_node_id` 设计
- `services/rag-service/app/services/rag_service.py` (lines 35-200) - Why: 索引调度、检索、重排和清理主逻辑
- `services/rag-service/app/routers/rag.py` (lines 10-79) - Why: 当前 RAG API 路由入口（project 前缀）
- `services/project-service/app/routers/projects.py` (lines 66-131, 114) - Why: 文件上传后会触发索引调度，需改为支持上传到 rag collection
- `services/project-service/app/services/rag_client.py` (lines 11-20) - Why: project-service 调用 rag-service 的 HTTP 客户端模式
- `services/project-service/app/models/project.py` (lines 13-34) - Why: project 模型需要新增激活 RAG 绑定字段（或关联表）
- `services/task-service/app/schemas/task.py` (lines 7-40) - Why: task DTO 当前含 model，不含 rag 选择，需要补充
- `services/task-service/app/models/task.py` (lines 25-37) - Why: task 落库字段边界与运行态绑定字段定义
- `services/task-service/app/routers/tasks.py` (lines 76, 86-87, 208, 166, 220) - Why: 创建任务、模型目录、发布 run 队列逻辑
- `worker/main.py` (lines 181-200, 412-445) - Why: 当前 worker 检索上下文入口仅按 project
- `worker/rag/retriever.py` (full file) - Why: 向量检索 where 子句目前硬编码 `DocumentChunk.project_id == project_id`
- `frontend/src/features/welcome/WelcomeScreen.tsx` (lines 41-58, 529-552) - Why: 当前 Chat 页面已有 project/conversation 与 Search/Code 控件
- `frontend/src/features/welcome/WelcomeScreen.module.css` (lines 89-205) - Why: 侧栏滚动、折叠箭头、菜单视觉需延续既有风格
- `nginx/nginx.conf` (lines 33, 45, 66) - Why: 网关路由约束，新增 API 要与现有前缀兼容
- `docker-compose.yml` (lines 75, 286-287) - Why: 服务 URL 与前端 API 基地址
- `backend/alembic/versions/1005_document_index_jobs_and_uuid_chunks.py` (lines 18-70) - Why: 迁移文件风格与约束命名样例

### New Files to Create

- `backend/alembic/versions/<rev>_global_rag_registry.py` - 新增全局 RAG 表与字段迁移
- `services/rag-service/app/models/rag_collection.py` - RAG 集合模型
- `services/rag-service/app/models/rag_collection_file.py` - RAG 文件资源模型
- `services/rag-service/app/schemas/rag_collection.py` - RAG 集合 DTO
- `services/rag-service/app/schemas/rag_file.py` - RAG 文件 DTO
- `services/rag-service/app/routers/rag_collections.py` - 全局 RAG CRUD + 上传列表 API
- `services/rag-service/tests/test_rag_collections_api.py` - RAG API 集成测试
- `services/project-service/app/schemas/project_rag.py` - project 绑定/查询 RAG 的 DTO
- `services/project-service/app/routers/project_rag.py` - project <-> rag 绑定 API
- `services/project-service/tests/test_project_rag_binding_api.py` - 绑定 API 测试
- `frontend/src/features/chat-rag/` (component files) - RAG/Model popover 和附件 chips（建议拆模块）
- `frontend/src/features/chat-rag/useRagCollections.ts` - RAG 列表与选择状态 hook
- `frontend/src/features/chat-rag/useModelCatalog.ts` - Model 列表 hook（可复用原模式）

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- Internal:
  - `README.md` (Current Architecture Baseline section lines 117-122)
    - Why: 当前真实调用链（task queue / run events / rag flow）基线
  - `docs/modules/rag-system-guide.md` (RAG 模型与调用链章节)
    - Why: 现有 RAG 技术债与调用点梳理
  - `.claude/reference/fastapi-best-practices.md`
    - Why: 路由、依赖注入、错误码风格统一
  - `.claude/reference/testing-and-logging.md`
    - Why: 日志和测试写法一致性

- External:
  - FastAPI APIRouter docs: https://fastapi.tiangolo.com/tutorial/bigger-applications/
    - Why: 新增 router 模块化注册
  - SQLAlchemy relationship patterns: https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html
    - Why: RAG 集合与文件的 one-to-many / project 绑定关系
  - pgvector SQLAlchemy usage: https://github.com/pgvector/pgvector-python
    - Why: 扩展 chunk 过滤键后的向量检索写法
  - Next.js App Router docs: https://nextjs.org/docs/app
    - Why: 单页 chat 内 popover + file input 行为实现边界

### Patterns to Follow

**Naming Conventions:**

- Python 模型字段与 schema：snake_case（参考 `task.py`, `project.py`）
- FastAPI 路由路径：资源复数 + REST 风格（参考 `projects.py`, `tasks.py`, `rag.py`）
- 前端状态与 handler：`useState` + `handleXxx`（参考 `WelcomeScreen.tsx`）

**Error Handling:**

- API 404/422/503 通过 `HTTPException` 抛出（参考 `tasks.py:create_task_run`, `projects.py:upload_project_file`）
- 前端统一捕获后显示可读错误字符串（`WelcomeScreen.tsx:requestJson/readableError`）

**Logging Pattern:**

- backend/service 使用 `structlog.get_logger(__name__)`（参考 queue_service / rag_service）
- 关键失败点记录 `error` + `exc_info=True`（参考 `tasks.py` publish failure 逻辑）

**Other Relevant Patterns:**

- Queue 发布后补偿失败状态（`tasks.py:166,220`）
- migration 采用独立 revision + 明确 FK/Index 命名（`1005_document_index_jobs...py`）
- 前端单页交互使用本地状态，不引入新全局状态库（当前仓库已收敛成单 chat 页）

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

定义全局 RAG 领域模型与数据库迁移，建立兼容策略。

**Tasks:**

- 新增 `rag_collections` / `rag_collection_files` 表
- 为 `projects` 新增 `active_rag_collection_id`（nullable）
- 为 `tasks` 新增 `rag_collection_id`（nullable，执行快照）
- 为 `document_chunk` / `document_index_jobs` 新增 `rag_collection_id`
- 为旧数据提供回填策略（至少保证不崩：null-safe + fallback project_id）

### Phase 2: Core Implementation

实现 RAG 集合 CRUD、上传、索引调度、检索过滤。

**Tasks:**

- rag-service 新增 `rag_collections` 路由组
- 上传文件进入 rag collection 文件表并发布 index-job
- 索引 worker 写 chunk 时附带 `rag_collection_id`
- 检索 service 支持按 `rag_collection_id` 查询
- project-service 新增绑定 API：project 选择/查询 active rag

### Phase 3: Integration

把 project 绑定、task 创建、worker 检索、chat UI 串起来。

**Tasks:**

- task-service `TaskCreate` 支持 `rag_collection_id`，创建任务时落库
- worker `retrieve_project_context` 优先读取 `task.rag_collection_id` 检索
- chat 输入区新增 `RAG` / `Model` 选择器
- 附件按钮接 file picker，选中文件显示在输入框上方 chips
- 上传文件目标改为当前选中 RAG，而非 project files

### Phase 4: Testing & Validation

覆盖迁移、API、worker 检索路径与前端交互边界。

**Tasks:**

- 后端新增单元/集成测试
- worker 检索过滤逻辑测试（rag_id 优先）
- 前端关键交互测试（popover、outside click、file picker）
- docker compose 全量构建回归

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE `backend/alembic/versions/<rev>_global_rag_registry.py`

- **IMPLEMENT**: 新增 `rag_collections`, `rag_collection_files`，并为 `projects/tasks/document_chunk/document_index_jobs` 增加 `rag_collection_id` 字段和索引
- **PATTERN**: `backend/alembic/versions/1005_document_index_jobs_and_uuid_chunks.py:18-70`
- **IMPORTS**: `sqlalchemy as sa`, `op`
- **GOTCHA**: 避免强制非空迁移，先 nullable + 回填脚本
- **VALIDATE**: `cd backend && uv run alembic upgrade head`

### CREATE `services/rag-service/app/models/rag_collection.py`

- **IMPLEMENT**: 定义全局 RAG 集合模型（id/name/description/timestamps）
- **PATTERN**: `services/project-service/app/models/base.py:6-12`
- **IMPORTS**: SQLAlchemy ORM + UUID
- **GOTCHA**: `name` 需要唯一约束（至少在租户模型缺失阶段全局唯一）
- **VALIDATE**: `cd services/rag-service && uv run pytest -q`

### CREATE `services/rag-service/app/models/rag_collection_file.py`

- **IMPLEMENT**: 定义 RAG 文件模型（rag_collection_id/storage_path/file_name/size/status）
- **PATTERN**: `services/rag-service/app/models/document_index_job.py:23-36`
- **IMPORTS**: Enum + FK + relationship
- **GOTCHA**: status 枚举需覆盖 pending/running/completed/failed
- **VALIDATE**: `cd services/rag-service && uv run pytest -q`

### UPDATE `services/rag-service/app/models/document_chunk.py`

- **ADD**: `rag_collection_id` 字段与检索索引
- **PATTERN**: 现有 `project_id` 索引写法（line 23）
- **IMPORTS**: FK 与 Index
- **GOTCHA**: 保留 `project_id` 兼容旧链路（迁移期）
- **VALIDATE**: `cd services/rag-service && uv run pytest tests/test_hybrid_retriever.py -q`

### UPDATE `services/rag-service/app/models/document_index_job.py`

- **ADD**: `rag_collection_id` 字段（支持按 RAG 调度）
- **PATTERN**: `project_node_id` 字段定义风格（line 30）
- **IMPORTS**: UUID FK
- **GOTCHA**: 与旧 `project_id` 字段共存阶段的状态更新一致性
- **VALIDATE**: `cd services/rag-service && uv run pytest -q`

### CREATE `services/rag-service/app/schemas/rag_collection.py`

- **IMPLEMENT**: Create/List/Update/Response DTO
- **PATTERN**: `services/project-service/app/schemas/project.py`
- **IMPORTS**: Pydantic v2 `ConfigDict`
- **GOTCHA**: Response 含 created_at/updated_at
- **VALIDATE**: `cd services/rag-service && uv run pytest -q`

### CREATE `services/rag-service/app/schemas/rag_file.py`

- **IMPLEMENT**: 上传与列表 DTO
- **PATTERN**: `ProjectFileUploadResponse` 风格
- **IMPORTS**: UUID, datetime
- **GOTCHA**: 文件状态与 index job 状态保持可追踪关系
- **VALIDATE**: `cd services/rag-service && uv run pytest -q`

### CREATE `services/rag-service/app/routers/rag_collections.py`

- **IMPLEMENT**: `GET/POST/PATCH/DELETE /api/rags` + `POST/GET /api/rags/{id}/files`
- **PATTERN**: `services/rag-service/app/routers/rag.py:10-79`
- **IMPORTS**: Depends(get_db), HTTPException, UploadFile
- **GOTCHA**: 上传后必须发布 index queue，发布失败要补偿为 failed
- **VALIDATE**: `cd services/rag-service && uv run pytest tests/test_rag_collections_api.py -q`

### UPDATE `services/rag-service/app/services/rag_service.py`

- **ADD**: search 支持 `rag_collection_id` 参数（优先），fallback 到旧 project_id
- **MIRROR**: `_vector_search` 当前 `DocumentChunk.project_id` 过滤（line 127）改为可切换过滤键
- **GOTCHA**: threshold/reranker/query rewrite 行为不变，避免回归
- **VALIDATE**: `cd services/rag-service && uv run pytest tests/test_hybrid_retriever.py tests/test_query_rewriter.py tests/test_reranker.py -q`

### UPDATE `services/rag-service/app/main.py`

- **ADD**: 注册 `rag_collections` router
- **PATTERN**: 现有 `app.include_router(rag.router)`
- **GOTCHA**: 保持 `/api/rag` 旧健康/路由不破坏
- **VALIDATE**: `cd services/rag-service && uv run uvicorn app.main:app --port 8003`

### CREATE `services/project-service/app/schemas/project_rag.py`

- **IMPLEMENT**: project 绑定/查询 RAG 的 DTO
- **PATTERN**: `ConversationCreate/Update/Response` 风格
- **IMPORTS**: UUID + BaseModel
- **GOTCHA**: 绑定接口要允许解绑（null）
- **VALIDATE**: `cd services/project-service && uv run pytest -q`

### CREATE `services/project-service/app/routers/project_rag.py`

- **IMPLEMENT**: `PUT /api/projects/{project_id}/rag` 与 `GET /api/projects/{project_id}/rag`
- **PATTERN**: `projects.py` 查询 project 的写法
- **IMPORTS**: HTTP client to rag-service for rag existence check
- **GOTCHA**: 绑定前校验 rag_id 是否存在，避免脏引用
- **VALIDATE**: `cd services/project-service && uv run pytest tests/test_project_rag_binding_api.py -q`

### UPDATE `services/project-service/app/main.py`

- **ADD**: include project_rag router
- **PATTERN**: `projects.router`, `conversations.router` 注册
- **GOTCHA**: tags/prefix 保持 `/api/projects/...` 风格一致
- **VALIDATE**: `cd services/project-service && uv run uvicorn app.main:app --port 8001`

### UPDATE `services/task-service/app/models/task.py`

- **ADD**: `rag_collection_id` nullable 字段（task 执行快照）
- **PATTERN**: `current_run_id` 与可空字段声明风格（line 35）
- **GOTCHA**: 不要破坏既有 queue_status 与 run 外键行为
- **VALIDATE**: `cd services/task-service && uv run pytest -q`

### UPDATE `services/task-service/app/schemas/task.py`

- **ADD**: `TaskCreate.rag_collection_id`、`TaskResponse.rag_collection_id`
- **PATTERN**: `model` 可选字段风格（line 13）
- **GOTCHA**: 保持旧客户端 payload 兼容（字段可选）
- **VALIDATE**: `cd services/task-service && uv run pytest -q`

### UPDATE `services/task-service/app/routers/tasks.py`

- **ADD**: create_task 时透传 rag_collection_id 落库
- **PATTERN**: create_task 数据处理流程（line 76）
- **GOTCHA**: model 解析逻辑不受影响（line 86-87）
- **VALIDATE**: `cd services/task-service && uv run pytest tests/test_models_api.py -q`

### UPDATE `worker/rag/retriever.py`

- **REFACTOR**: `retrieve/_search_similar_chunks` 支持按 `rag_collection_id` 检索
- **PATTERN**: 当前 where 子句（project_id）
- **GOTCHA**: 两种过滤键并存时的优先级（rag > project）
- **VALIDATE**: `cd worker && uv run pytest tests/test_retriever.py -q`

### UPDATE `worker/main.py`

- **UPDATE**: `retrieve_project_context` 传递 `task.rag_collection_id`（若为空 fallback project）
- **PATTERN**: 现有 call chain `retrieve_project_context -> DocumentRetriever.retrieve`（lines 181-200, 412-445）
- **GOTCHA**: task schema/model 同步后再改 worker，避免属性缺失
- **VALIDATE**: `cd worker && uv run pytest tests/test_main.py tests/test_agent.py -q`

### UPDATE `frontend/src/features/welcome/WelcomeScreen.tsx`

- **ADD**: RAG popover（读取 `GET /api/rags`），Model popover（`GET /api/tasks/models`）
- **ADD**: 附件按钮触发 hidden file input，展示 selected file chips 于输入框上方
- **ADD**: 上传动作 `POST /api/rags/{rag_id}/files/upload`
- **ADD**: 创建任务 payload 附带 `rag_collection_id` + `model`
- **PATTERN**: 当前 requestJson/error handling 与菜单 outside click 处理（lines 140-431）
- **GOTCHA**: 单页模式下避免死链接依赖，popover 点击外部关闭与 rename 面板互斥
- **VALIDATE**: `cd frontend && npm run type-check`

### UPDATE `frontend/src/features/welcome/WelcomeScreen.module.css`

- **ADD**: RAG/Model popover、file chips、input toolbar 扩展样式
- **PATTERN**: 现有菜单与折叠动画类（lines 138-205）
- **GOTCHA**: 小屏下输入区高度与滚动行为不冲突
- **VALIDATE**: `cd frontend && npm run lint`

### UPDATE `nginx/nginx.conf`

- **ADD**: 确认 `/api/rags` 路由转发到 rag-service（若采用该前缀）
- **PATTERN**: `location /api/rag` / `location /api/projects` 样式
- **GOTCHA**: 避免覆盖既有 `/api/rag` 前缀规则
- **VALIDATE**: `docker compose -f docker-compose.yml up -d --build api-gateway`

### ADD Tests

- **CREATE**: rag-service API tests for rag CRUD/file upload/index schedule/search by rag id
- **CREATE**: project-service binding tests
- **UPDATE**: worker retriever tests for rag-id filter branch
- **UPDATE**: frontend tests for popover select + file chips render
- **VALIDATE**: 见 “VALIDATION COMMANDS”

---

## TESTING STRATEGY

### Unit Tests

- rag-service: model/schema/validation for rag entities
- task-service: task schema/model include rag_collection_id
- worker: retriever filter key selection
- frontend: hook/component state transitions for selectors and file chips

### Integration Tests

- 创建 RAG -> 上传文件 -> 生成 index job -> worker 消费 -> chunk 入库 -> 检索返回
- Project 绑定 RAG -> 创建 Task -> Worker 检索使用绑定 RAG
- Chat 页面：选择 RAG/Model + 上传附件 + 发消息任务创建 payload 校验

### Edge Cases

- Project 未绑定 RAG（fallback 行为）
- RAG 被删除但 project/task 仍引用（运行期错误码与提示）
- 同名 RAG 创建冲突
- 上传失败/队列发布失败补偿状态
- 旧数据没有 rag_collection_id 的兼容查询
- 前端 popover 与 rename 面板同时打开冲突

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

- `cd frontend && npm run lint`
- `cd frontend && npm run type-check`
- `cd services/project-service && uv run pytest -q`
- `cd services/task-service && uv run pytest -q`
- `cd services/rag-service && uv run pytest -q`
- `cd worker && uv run pytest -q`

### Level 2: Unit Tests

- `cd services/rag-service && uv run pytest tests/test_hybrid_retriever.py tests/test_query_rewriter.py tests/test_reranker.py -q`
- `cd services/task-service && uv run pytest tests/test_models_api.py -q`
- `cd worker && uv run pytest tests/test_retriever.py tests/test_main.py -q`

### Level 3: Integration Tests

- `cd backend && uv run pytest tests/test_contract_execution_apis.py -q`
- `cd services/project-service && uv run pytest tests/test_project_rag_binding_api.py -q`
- `cd services/rag-service && uv run pytest tests/test_rag_collections_api.py -q`

### Level 4: Manual Validation

1. 创建两个 RAG（A/B）
2. 上传同一文档到 RAG A，确认索引完成
3. 在 Project P1 绑定 RAG A，在 Project P2 绑定 RAG A
4. 在 P1/P2 Chat 中都选择 RAG A 发起检索任务，验证返回同源文档上下文
5. 将 P2 切换绑定到 RAG B，验证检索结果切换
6. 在 Chat 输入区验证：
   - 附件按钮唤起系统文件选择器
   - 已选文件 chips 展示
   - RAG/Model 选择器可用且落库到 task

### Level 5: Additional Validation (Optional)

- `docker compose -f docker-compose.yml up --build -d`
- `docker compose -f docker-compose.yml ps`
- `curl http://localhost/health`
- `curl http://localhost:8001/health && curl http://localhost:8002/health && curl http://localhost:8003/health`

---

## ACCEPTANCE CRITERIA

- [ ] 可创建多个全局 RAG 集合
- [ ] 一个 RAG 可被多个 Project 绑定复用
- [ ] Project 可切换绑定不同 RAG
- [ ] Chat 输入区支持 RAG 选择、Model 选择、附件上传与文件 chips 展示
- [ ] Task 记录包含 rag_collection_id 与 model
- [ ] Worker 检索优先按 rag_collection_id 生效
- [ ] 所有验证命令通过
- [ ] 无现有任务队列/事件流回归

---

## COMPLETION CHECKLIST

- [ ] Migration 完成并可回滚
- [ ] rag-service API 与索引链路完成
- [ ] project-service 绑定 API 完成
- [ ] task-service task schema/model/router 完成
- [ ] worker 检索过滤逻辑完成
- [ ] chat 前端选择/上传交互完成
- [ ] lint + type-check + test + compose 全通过
- [ ] 手工场景验证通过

---

## NOTES

- 关键架构决策：
  - v1 采用“Project 绑定 1 个 active RAG”，并在 Task 中快照 `rag_collection_id`，保障运行一致性。
  - 检索逻辑采用 `rag_collection_id` 优先，`project_id` fallback，降低迁移风险。
- 主要风险：
  1. 历史数据兼容（旧 chunk 无 rag id）
  2. 跨服务模型同步不一致导致运行期字段缺失
  3. 上传/索引失败补偿状态遗漏
- 回滚策略：
  - 保持旧 project-based API 在过渡期可用
  - migration 分两步（schema add -> backfill -> enforce）

Confidence Score: **8.3/10** for one-pass implementation success.
