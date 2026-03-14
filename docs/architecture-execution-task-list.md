# Badgers MVP 架构改造可执行任务清单

## 1. 文档定位

本文把下面两份文档收敛成一份真正可执行的主任务清单：

- `docs/target-architecture-gap-analysis.md`
- `docs/rag-refactor-plan.md`

这份文档不再只回答“要做什么”，而是明确回答下面四件事：

1. 当前代码具体卡在哪里
2. 这项任务的推荐解决方案是什么
3. 应该改哪些文件、补哪些边界
4. 什么状态算真正完成

如果后续需要 `compact` 后继续推进这条主线，默认只读本文件即可。

---

## 2. 执行原则

1. 先收口，再扩展
2. 先打通主执行链，再补界面
3. 继续保持“模块化单体 + 独立 worker”，本轮不拆微服务
4. RAG 并入主链，不再单独并行维护
5. 所有方案都以当前仓库真实代码为起点，不按 PRD 假设项目已经实现

---

## 3. 执行顺序总览

```text
Phase 0 运行基线与配置收口
  ->
Phase 1 Worker 协议统一
  ->
Phase 2 TaskRun 执行闭环
  ->
Phase 3 实时事件与 Artifact 闭环
  ->
Phase 4 RAG 收敛与接入
  ->
Phase 5 Frontend 业务页面补齐
  ->
Phase 6 基础设施与交付收尾
```

说明：

- `Phase 1-4` 是核心主线
- `Phase 5` 依赖 `Phase 2-4`
- `Phase 6` 是稳定化和交付层

---

## 4. 优先级定义

| 优先级 | 含义 |
|---|---|
| P0 | 不完成则主执行链无法闭环 |
| P1 | 主执行链闭环后，补足关键可用性 |
| P2 | 提升完整性、维护性和交付质量 |

---

## 5. 可执行任务清单

## Phase 0：运行基线与配置收口

### Task 0.1：统一环境变量命名与配置来源

优先级：`P0`

目标：
让 `backend`、`worker`、`.env.example`、`docker-compose.yml`、`README.md` 使用同一套配置命名，并解决当前对象存储配置和默认值冲突。

当前实现锚点：

- `backend/app/config.py` 读取的是 `minio_*`
- `backend/app/services/storage.py` 直接把 `settings.minio_endpoint` 传给 `Minio(...)`
- `.env.example` 提供的是 `S3_*`
- `.env.example` 的 `S3_ENDPOINT=http://localhost:9000` 与 MinIO Python SDK 期望的 `host:port` 格式不一致
- `backend/app/config.py` 的默认数据库密码、MinIO 默认凭证与 `.env.example` / `docker-compose.yml` 不一致
- `worker/config.py` 目前没有对象存储和 RAG 相关配置，后续 RAG/Artifact 接入会继续分叉

解决方案：

1. 以 `S3_*` 作为跨服务统一外部环境变量命名
2. `backend` 内部不再把对象存储配置命名为 `minio_*`，统一改成 `s3_*`
3. 保留 `MINIO_*` 仅作为兼容别名时，必须明确标注为 deprecated，不再作为主命名
4. 统一默认值到当前仓库实际开发组合：
   - `DATABASE_URL=postgresql://badgers:badgers_dev_password@localhost:5432/badgers`
   - `S3_ENDPOINT=localhost:9000`
   - `S3_ACCESS_KEY=badgers`
   - `S3_SECRET_KEY=badgers_dev_password`
   - `S3_BUCKET=badgers-artifacts`
   - `S3_SECURE=false`
5. 在 `worker/config.py` 中补齐对象存储、embedding、RAG 查询所需配置，避免后续 worker 直接硬编码

具体改动：

- 修改 `backend/app/config.py`
  - 用 `s3_endpoint / s3_access_key / s3_secret_key / s3_bucket / s3_secure`
  - 默认值对齐 `.env.example`
- 修改 `backend/app/services/storage.py`
  - 改为读取 `settings.s3_*`
  - 不再接受带 scheme 的 endpoint
- 修改 `worker/config.py`
  - 新增 `s3_*`
  - 新增 `embedding_model`
  - 新增后续 RAG 调度需要的配置占位
- 修改 `.env.example`
  - 改掉 `S3_ENDPOINT` 的 URL 形式
  - 补 `S3_SECURE`
- 修改 `README.md`
  - 配置示例与代码一致
- 修改 `docker-compose.yml`
  - 环境变量示例与 `.env.example` 一致

交付物：

- 一套统一的环境变量命名规则
- 一套一致的默认值
- 统一的 README 配置说明

验收标准：

- backend 和 worker 能从同一份 `.env` 成功启动
- README 中出现的配置名全部能在代码里找到
- 对象存储配置不再同时出现一套 `S3_*` 和一套主链 `minio_*`

依赖：
无

---

### Task 0.2：稳定 backend 测试基础设施

优先级：`P0`

目标：
把 backend 测试从“默认依赖真实 PostgreSQL 连通”收敛为“单元测试可直接跑，集成测试显式依赖 DB”。

当前实现锚点：

- `backend/tests/conftest.py` 的 session 级 `init_test_db()` 直接调用 `app.database.init_db()`
- `app.database.engine` 在导入时就绑定 `settings.database_url`
- 当前 API 测试大多是“真路由 + 真 DB”风格
- `DocumentChunk.embedding` 使用 `pgvector`，这意味着不能把整套测试简单粗暴切到 SQLite

解决方案：

1. 不强行把当前全部 backend API 测试迁到 SQLite
2. 把测试拆成两层：
   - `unit` / `contract`：默认可跑，不依赖真实 PostgreSQL
   - `integration`：显式依赖 PostgreSQL + pgvector
3. backend 默认测试基线采用“依赖覆盖 + mock session / mock service”的方式验证 router 行为
4. 保留少量真正打数据库的集成测试，但改为：
   - 读取 `TEST_DATABASE_URL`
   - 未提供时自动 `skip`
5. RAG/vector 相关测试全部归入 `integration`，不要假装它们能在 SQLite 下稳定成立

具体改动：

- 修改 `backend/tests/conftest.py`
  - 去掉无条件 `init_db()`
  - 新增 `unit_app_client` fixture
  - 新增 `integration_db` fixture
- 调整 `backend/tests/test_api_*.py`
  - 按类型拆分
  - 能用依赖覆盖的路由先改成 unit/contract 测试
- 保留 `backend/tests/test_chunker.py` / `test_embeddings.py` / `test_indexer.py` / `test_retriever.py`
  - 但需要明确标记哪些是 backend 历史遗留、哪些在 Task 4.1 后要迁移或删除
- 更新 `docs/testing-guidelines.md`
  - 新增 unit / integration 的运行方式

交付物：

- backend 测试分层规则
- 默认不依赖真实外部 DB 的基础测试集
- 显式受控的 integration 测试入口

验收标准：

- 至少一组 backend API 测试可以在没有手工准备 PostgreSQL 的情况下跑通
- integration 测试未配置 DB 时会跳过，而不是直接连接失败
- `docs/testing-guidelines.md` 写清楚运行方式

依赖：
无

---

## Phase 1：Worker 协议统一

### Task 1.1：统一模型 provider 协议

优先级：`P0`

目标：
让 worker 的模型层只保留一套 Agent 真正在使用的协议。

当前实现锚点：

- `worker/orchestrator/agent.py` 依赖的是 `models.tool_calling.ModelProvider`
- `worker/models/factory.py` 返回的是 `models.openai_provider.OpenAIProvider` / `models.anthropic_provider.AnthropicProvider`
- `worker/models/openai_provider.py` 和 `worker/models/anthropic_provider.py` 实现的是 `generate/stream`
- `worker/models/openai_compat.py` 和 `worker/models/anthropic_native.py` 已经实现了 `chat_completion + tool_calls`

解决方案：

1. 把 `models.tool_calling.py` 定义为 worker 模型主协议
2. `factory.py` 直接切到返回：
   - `openai_compat.OpenAIProvider`
   - `anthropic_native.AnthropicProvider`
3. `models/base.py` / `models.types.py` 不再承载 Agent 主链协议
4. 如果 `ProviderType`、`ModelConfig` 仍需保留，可以保留为“配置类型”，但不能再与 Agent 消息协议混用
5. 所有 provider 测试改为验证 `chat_completion()` 输出 `ModelResponse`

具体改动：

- 修改 `worker/models/factory.py`
  - 改导入路径到 `openai_compat.py` 和 `anthropic_native.py`
  - 返回类型改为 `ModelProvider`
- 修改 `worker/models/openai_compat.py`
  - 补齐工厂需要的构造参数
  - 对齐 `settings`
- 修改 `worker/models/anthropic_native.py`
  - 同步工厂构造参数
- 弱化或删除主链对以下文件的依赖：
  - `worker/models/base.py`
  - `worker/models/openai_provider.py`
  - `worker/models/anthropic_provider.py`
- 修改测试：
  - `worker/tests/test_models_factory.py`
  - `worker/tests/test_agent.py`
  - 新的 provider 测试应围绕 `chat_completion`

交付物：

- 单一模型 provider 协议
- 与 Agent 一致的工厂返回值
- 同步更新后的测试

验收标准：

- `Agent.run()` 能通过 `create_model_provider()` 返回对象正常调用
- 工厂不再返回 `generate/stream` 风格 provider
- 相关 worker 模型测试通过

依赖：

- Task 0.1

---

### Task 1.2：统一工具协议并纳入文件工具

优先级：`P0`

目标：
让 worker 只保留一套工具协议，并把文件工具纳入默认工具集。

当前实现锚点：

- `worker/orchestrator/agent.py` 依赖 `tools.tool_base.Tool`
- `worker/tools/browser.py` / `python.py` / `web.py` 实现的是 `BaseTool`
- `worker/tools/file.py` 实现的是 `Tool`
- `worker/tools/__init__.py` 只注册了 Browser / Web / Python，没注册文件工具

解决方案：

1. 把 `worker/tools/tool_base.py` 作为唯一工具协议
2. `browser.py`、`python.py`、`web.py` 全部改成实现 `Tool`
3. `BaseTool` 从主链退出，最多只保留过渡适配层
4. `get_all_tools()` 默认返回：
   - `BrowserTool`
   - `WebFetchTool`
   - `PythonTool`
   - `FileListTool`
   - `FileReadTool`
   - `FileWriteTool`
5. 统一 `ToolResult`
   - 统一 `success / output / error`
   - 附加字段通过 metadata 承载，不再每个工具自定义完全不同的外形

具体改动：

- 修改 `worker/tools/browser.py`
  - 增加 `name / description / parameters`
  - `execute(**kwargs) -> ToolResult`
  - 保留原子操作 `open/click/type/extract/screenshot`
- 修改 `worker/tools/python.py`
  - 从 `BaseTool.execute(params)` 改为 `Tool.execute(**kwargs)`
  - 标准化输出
- 修改 `worker/tools/web.py`
  - 同样改成 `Tool`
- 修改 `worker/tools/__init__.py`
  - 注册文件工具
- 视情况删除或弱化 `worker/tools/base.py`
- 调整测试：
  - `worker/tests/test_agent.py`
  - `worker/tests/test_tools.py`
  - `worker/tests/test_browser_tools.py`
  - `worker/tests/test_python_tool.py`
  - `worker/tests/test_web_tool.py`

交付物：

- 单一 Tool 接口
- 默认工具集包含文件工具
- 更新后的工具测试

验收标准：

- Agent 能实际调用 `file_list / file_read / file_write`
- Browser、Web、Python、File 工具都走同一协议
- `get_all_tools()` 返回值可直接喂给 Agent

依赖：

- Task 1.1

---

### Task 1.3：明确工具的 sandbox 执行边界

优先级：`P1`

目标：
明确哪些工具必须在 sandbox 里执行，并把这个边界真正落进代码结构，而不是只写在文档里。

当前实现锚点：

- `PythonTool` 通过 `SandboxManager.execute()` 在容器里执行
- `BrowserTool` 当前直接在 worker 进程里启动 Playwright
- `WebFetchTool` 当前直接在 worker 进程里发 HTTP
- `File*Tool` 默认读写 `/workspace`，但 `DockerBackend` 并没有把宿主目录挂载进容器

解决方案：

1. 明确第一阶段执行边界：
   - `python`：必须 sandbox
   - `file`：必须 sandbox
   - `browser`：建议 sandbox，若短期不做，则必须显式标记为 host-executed
   - `web`：可先 host-executed，但必须在文档中标明
2. 为 sandbox 引入“可见工作目录”能力
   - 在 `DockerBackend.create_container()` 中增加宿主目录挂载到容器 `/workspace`
   - `SandboxManager` 暴露该 workspace 路径
3. 文件工具只允许操作该 workspace，不允许直接读写 worker 宿主任意路径
4. 若 browser 仍暂时在 host 执行，截图产物也必须落在该 workspace，不能散落在 worker 进程任意路径

具体改动：

- 修改 `worker/sandbox/docker_backend.py`
  - 增加 bind mount
  - 增加必要时的文件拷出/读写辅助方法
- 修改 `worker/sandbox/manager.py`
  - 暴露 `workspace_dir`
- 修改 `worker/tools/file.py`
  - 工作目录来源于 sandbox workspace
  - 增加路径越界校验
- 修改 `worker/tools/browser.py`
  - 截图默认路径落在 workspace
  - 文档注明当前是否 host 执行
- 更新 `docs/current-system-architecture.md`
  - 把真实隔离边界写清楚

交付物：

- 清晰的工具执行位置策略
- 可复用的 sandbox workspace 机制
- 代码与文档一致的边界定义

验收标准：

- `python` 和 `file` 工具都通过 sandbox workspace 工作
- 文档明确写出 `browser` / `web` 当前是否仍在 host 执行
- 不再出现文件工具默认读写 worker 宿主任意目录的情况

依赖：

- Task 1.2

---

## Phase 2：TaskRun 执行闭环

### Task 2.1：完善 TaskRun 生命周期与 `current_run_id`

优先级：`P0`

目标：
让 `Task -> TaskRun` 的状态关系闭环，并让前端能从 Task 读到真实活动 Run。

当前实现锚点：

- `backend/app/models/task.py` 已有 `current_run_id`
- `backend/app/routers/tasks.py:create_task_run()` 创建 Run 时没有回写 `Task.current_run_id`
- `worker/main.py:get_next_pending_task()` 会把 Run 从 `pending` 改为 `running`
- `worker/main.py:execute_task_run()` 完成和失败时只更新 `TaskRun`，不会处理 `Task.current_run_id`
- `backend/app/routers/runs.py:cancel_run()` 也不会清理 Task 的活动 run 指针

解决方案：

1. 在创建 Run 时立即写回 `Task.current_run_id = new_run.id`
2. 在 worker claim Run 时只允许 claim：
   - `Task.current_run_id == 当前 run`
   - 或者 `Task.current_run_id is null` 且当前 run 为最新 pending run
3. Run 进入终态时统一清理 Task 指针：
   - `completed`
   - `failed`
   - `cancelled`
4. 所有状态变更都统一记录时间字段
5. 对取消中的竞态做保护：
   - worker 执行前再次检查 run 是否仍为 `RUNNING`
   - 若已被取消，直接退出

具体改动：

- 修改 `backend/app/routers/tasks.py`
  - `create_task_run()` 中查询 Task 实体后回写 `current_run_id`
- 修改 `backend/app/routers/runs.py`
  - `cancel_run()` 时同步清理 Task 指针
- 修改 `worker/main.py`
  - claim 后、执行前、完成后、失败后都维护 Task 指针
  - 增加取消状态检查
- 视需要调整 `backend/app/schemas/task.py`
  - 保证前端能拿到 `current_run_id`

交付物：

- Task 与当前活动 Run 的一致性逻辑
- 完整的状态流转
- 对取消/失败/完成的统一收口

验收标准：

- 创建 Run 后，Task 读取到正确的 `current_run_id`
- Run 从 `pending -> running -> completed/failed/cancelled` 流转一致
- Run 进入终态后，Task 的 `current_run_id` 被清空

依赖：

- Task 1.1
- Task 1.2

---

### Task 2.2：确定调度方式并固化实现

优先级：`P0`

目标：
停止文档和代码对调度方式的双重叙述，明确本轮主链就是 DB 轮询。

当前实现锚点：

- `worker/main.py` 当前通过查询 `TaskRun.status == PENDING` 轮询数据库
- `.env.example` / `README.md` / 架构图仍把 Redis/Queue 写成主链
- `docker-compose.yml` 虽然有 Redis，但真实执行链没有用它

解决方案：

1. 本轮正式确定：TaskRun 主链调度方式为“数据库轮询”
2. Redis 从“主链组件”降级为“保留基础设施，占位未来能力”
3. 所有文档必须改成：
   - 当前：DB polling
   - 未来可选：Redis queue
4. worker 中把 DB polling 封装成明确的 scheduler 逻辑，而不是散在 `main.py` 的临时代码

具体改动：

- 修改 `worker/main.py`
  - 把 `get_next_pending_task()` 抽成明确的调度/claim 逻辑
  - 明确注释“当前调度基线”
- 修改 `README.md`
  - 架构图和 Quick Start 不再宣称 Redis 是当前主执行队列
- 修改 `docker-compose.yml`
  - Redis 标记为 optional / future queue support
- 修改 `docs/current-system-architecture.md`
  - 写实当前状态

交付物：

- 明确的调度基线
- 代码与 README 对齐的系统描述

验收标准：

- README 不再出现“主链依赖 Redis queue”这种与代码冲突的表述
- 当前 worker 调度逻辑在文档中被明确命名为 DB polling

依赖：

- Task 2.1

---

### Task 2.3：补全 Retry API 和 Run 日志能力

优先级：`P1`

目标：
让 Run 不再只是一次性黑盒执行，而是可重试、可追踪。

当前实现锚点：

- `TaskRun.logs` 和 `TaskRun.working_memory` 字段已存在
- `backend/app/routers/tasks.py` 只有 `POST /tasks/{task_id}/runs`
- `backend/app/routers/runs.py` 只有 get / cancel / websocket
- 前端没有任何历史日志读取入口

解决方案：

1. 新增显式 retry 入口，而不是让前端重新拼一次 create run
2. `TaskRun.logs` 统一采用“结构化事件列表”格式，不存散乱字符串
3. worker 每次关键节点都把事件附加到 `logs`
4. 运行前检索到的 RAG context、关键输入摘要可以写入 `working_memory`

具体改动：

- 修改 `backend/app/routers/tasks.py`
  - 新增 `POST /api/tasks/{task_id}/retry`
  - 内部逻辑仍然是创建一个新的 `TaskRun`
- 修改 `backend/app/routers/runs.py`
  - 新增历史日志读取接口，或把 `logs` 直接带进 run detail
- 修改 `backend/app/schemas/task.py`
  - 扩展 `TaskRunResponse` 或新增详情 schema
- 修改 `worker/main.py`
  - 在 claim、sandbox 创建、agent 完成、失败、artifact 创建、RAG 检索等节点写入结构化日志

交付物：

- 显式 retry API
- 可读的 run event logs
- 可扩展的 working memory 存储

验收标准：

- 用户能针对同一 Task 创建新的 Run，而不需要重建 Task
- 至少能从 API 读到结构化执行日志

依赖：

- Task 2.1

---

## Phase 3：实时事件与 Artifact 闭环

### Task 3.1：接通 worker 到 backend 的执行事件流

优先级：`P0`

目标：
让前端看到的 WebSocket 事件来自真实执行过程，而不是只有取消事件。

当前实现锚点：

- `backend/app/services/event_broadcaster.py` 是 backend 进程内存里的连接管理器
- `backend/app/routers/runs.py` 只有 `cancel_run()` 在 broadcast
- `worker` 与 `backend` 是独立进程，worker 不能直接调用 backend 进程内的 broadcaster 实例
- `frontend/src/features/tasks/useTaskRunStream.ts` 已经能消费 websocket，但当前消息源几乎为空

解决方案：

1. 不要让 worker 直接 import broadcaster 试图发事件，这在进程边界上是无效的
2. backend 新增“事件摄取入口”，由 backend 进程负责：
   - 接收 worker 上报事件
   - 追加到 `TaskRun.logs`
   - 转发给 websocket broadcaster
3. worker 新增轻量 backend client，把事件通过 HTTP 发给 backend
4. 统一事件 schema，至少包括：
   - `run_started`
   - `step`
   - `tool_call`
   - `tool_result`
   - `artifact_created`
   - `run_completed`
   - `run_failed`

具体改动：

- 修改 `backend/app/routers/runs.py`
  - 新增内部事件写入入口，例如 `POST /api/runs/{run_id}/events`
- 修改 `backend/app/services/event_broadcaster.py`
  - 保持现有 in-memory broadcaster，但只作为 backend 进程内转发器
- 修改 `worker/main.py`
  - 在关键节点发事件
- 修改 `worker/orchestrator/agent.py`
  - 支持注入 event callback
  - 在 iteration / tool call / tool result 时回调
- 新增 worker 内部 backend client
  - 可放在 `worker/services/backend_client.py`
- 修改前端：
  - `frontend/src/features/tasks/types.ts`
  - `frontend/src/features/tasks/components/ExecutionTimeline.tsx`

交付物：

- backend 事件摄取入口
- worker 真实事件上报
- 对齐后的前端事件类型

验收标准：

- 运行任务时，前端能收到真实的执行事件
- `TaskRunViewer` 不再只展示取消事件
- 事件历史可在 `TaskRun.logs` 中看到

依赖：

- Task 2.1
- Task 2.2
- Task 2.3

---

### Task 3.2：实现 Artifact 自动产出链

优先级：`P0`

目标：
让工具和执行过程产生的文件自动进入 Artifact 体系。

当前实现锚点：

- `backend/app/models/artifact.py` 和 `backend/app/routers/artifacts.py` 已有手工上传/下载/删除
- worker 执行过程中不会自动创建 Artifact
- `BrowserTool.screenshot()`、`FileWriteTool.execute()` 已经有天然产物点
- 当前 sandbox 尚未保证 worker 能稳定拿到容器工作区文件

解决方案：

1. 不再把 Artifact 仅理解为手工上传资源
2. 为工具结果增加统一的 artifact metadata 返回能力
   - 例如 `artifact_candidates`
   - 或 `ToolResult.metadata`
3. worker 在收到工具结果后，判断是否需要注册 Artifact
4. Artifact 注册流程固定为：
   - 从 workspace 读取文件
   - 上传对象存储
   - 写 `Artifact` 表
   - 发 `artifact_created` 事件
5. 首批只覆盖明确产物型工具：
   - `file_write`
   - `browser.screenshot`
   - 后续再扩展 report/code/data

具体改动：

- 修改 `worker/tools/tool_base.py`
  - 为 `ToolResult` 增加 metadata
- 修改 `worker/tools/file.py`
  - `file_write` 返回生成文件路径、大小、mime 信息
- 修改 `worker/tools/browser.py`
  - `screenshot` 返回文件元信息
- 修改 `worker/main.py` 或新增 `worker/services/artifact_service.py`
  - 负责把工具产物注册为 Artifact
- 复用或扩展对象存储逻辑
  - 如有必要，把 backend/worker 共用的存储配置抽到统一方式
- backend 侧继续复用：
  - `backend/app/models/artifact.py`
  - `backend/app/services/storage.py`

交付物：

- 工具产物自动注册 Artifact
- Artifact metadata 入库
- Artifact 创建事件

验收标准：

- 执行任务生成文件后，可查到对应 Artifact
- Artifact 下载链路正常
- 前端实时流能看到 `artifact_created`

依赖：

- Task 1.3
- Task 3.1

---

### Task 3.3：实现 save-to-project 流转

优先级：`P1`

目标：
补上 `Artifact -> ProjectNode` 的显式保存动作。

当前实现锚点：

- `Artifact` 与 `ProjectNode` 已分层
- `ProjectNode.path` 存的是对象存储路径
- 当前没有 API 把 Artifact 保存成项目正式文件
- 若简单复用 Artifact 的 `storage_path`，删除 Artifact 时会把项目文件一起删坏

解决方案：

1. 新增显式 `save-to-project` API
2. 保存动作不是只写一条 `ProjectNode` 记录，而是要生成项目文件自己的对象存储路径
3. 对象存储层补 `copy_file()`，或退化为 `download + upload`
4. `ProjectNode` 默认保存到项目根目录，后续再扩展目录选择

具体改动：

- 修改 `backend/app/routers/artifacts.py`
  - 新增 `POST /api/artifacts/{artifact_id}/save-to-project`
- 修改 `backend/app/services/storage.py`
  - 新增对象复制能力
- 修改 `backend/app/models/project.py`
  - 复用 `ProjectNode`，无需改表结构
- 若需要返回结构化结果，补 schema

交付物：

- save-to-project API
- ProjectNode 写入逻辑
- 对象存储复制逻辑

验收标准：

- 用户可将 Artifact 保存为项目正式文件
- 删除 Artifact 后，不会把已保存的项目文件一起删除

依赖：

- Task 3.2

---

## Phase 4：RAG 收敛与接入

### Task 4.1：收敛 RAG 单一实现源

优先级：`P0`

目标：
停止维护两套 RAG 实现，先以 `worker/rag` 为唯一基线。

当前实现锚点：

- `backend/rag/*` 和 `worker/rag/*` 同时存在
- `worker/rag` 的 parser、embedding retry、chunker 更完整
- `backend/app/routers/rag.py` 当前只是 API 外壳，`index/search` 仍是 stub
- backend tests 中仍有 `rag.indexer` / `rag.retriever` 相关历史测试

解决方案：

1. 短期保留 `worker/rag` 作为唯一真实实现
2. backend 不再直接依赖 `backend/rag/*`
3. `backend/rag/*` 进入废弃态，待 backend 调整完成后删除
4. backend tests 中针对 `backend/rag` 的测试要么迁到 worker，要么在共享包阶段重建

具体改动：

- 标记以下目录为废弃：
  - `backend/rag/chunker.py`
  - `backend/rag/embeddings.py`
  - `backend/rag/indexer.py`
  - `backend/rag/retriever.py`
- 调整 backend 中对 RAG 的调用路径，全部改走 service / 单一实现
- 迁移或删除以下测试：
  - `backend/tests/test_chunker.py`
  - `backend/tests/test_embeddings.py`
  - `backend/tests/test_indexer.py`
  - `backend/tests/test_retriever.py`

交付物：

- 单一 RAG 实现基线
- backend 不再依赖 `backend/rag`

验收标准：

- backend 主链代码不再 import `backend/rag/*`
- 仓库中不存在“两套都在主链运行”的 RAG 实现

依赖：

- Task 0.1

---

### Task 4.2：新增 backend RAG orchestration service

优先级：`P0`

目标：
让 backend 只承担 RAG 控制面，而不是承担底层 parser/chunker/embedding 执行。

当前实现锚点：

- `backend/app/routers/rag.py` 用内联 Pydantic 请求模型，但 `index/search` 是固定 stub
- `backend/app/routers/projects.py:upload_project_file()` 上传后不会触发任何 RAG 动作

解决方案：

1. 新增 `backend/app/services/rag_service.py`
2. 该 service 只负责控制面：
   - 调度索引任务
   - 封装查询接口
   - 管理状态与错误
3. `backend/app/routers/rag.py` 不再自己写假逻辑，全部改调 service
4. 后端公开的 search API 可以使用“单一 RAG 实现”的 retriever，但不应该再保留 backend 自己的一整套 RAG 代码

具体改动：

- 新增 `backend/app/services/rag_service.py`
  - `schedule_indexing(project_id, node_id, storage_path, file_name)`
  - `search(project_id, query, top_k, threshold)`
  - `list_chunks(project_id)`
- 修改 `backend/app/routers/rag.py`
  - index/search 改为真实调用 service
- 修改 `backend/app/routers/projects.py`
  - 上传成功后调用 `rag_service.schedule_indexing(...)`

交付物：

- backend RAG orchestration service
- 非 stub 的 RAG router

验收标准：

- `backend/app/routers/rag.py` 不再返回固定假数据
- 上传项目文件后，backend 会触发索引调度

依赖：

- Task 4.1

---

### Task 4.3：接通文件上传后的索引任务

优先级：`P0`

目标：
让项目文件上传后自动进入真实索引流程。

当前实现锚点：

- `backend/app/routers/projects.py` 目前只做校验、存储、写 `ProjectNode`
- `worker/rag/indexer.py` 的 `content` 参数名存在，但内部仍按 `file_path` 读取文件
- 当前仓库没有专门的索引任务表，也没有 worker 索引 job 入口

解决方案：

1. 明确采用“对象存储下载到临时文件后索引”的路线
2. 不再继续保留“API 传 raw content 给 indexer，但 indexer 仍按文件路径解析”的半成品方式
3. 新增专用索引任务模型，例如：
   - `DocumentIndexJob`
   - 字段包括 `project_id / project_node_id / storage_path / status / error_message`
4. worker 扩展为同时处理：
   - `TaskRun`
   - `DocumentIndexJob`
5. worker 处理索引任务时：
   - 从对象存储下载文件到临时目录
   - 调用 `worker/rag/indexer.py`
   - 写入 `document_chunk`

具体改动：

- 新增 backend 模型与迁移：
  - `backend/app/models/document_index_job.py`
  - `backend/alembic/versions/*`
- 修改 `backend/app/routers/projects.py`
  - 上传成功后创建 `DocumentIndexJob`
- 修改 `worker/main.py`
  - 增加索引 job 轮询与处理逻辑
- 修改 `worker/rag/indexer.py`
  - 明确只支持“文件路径输入”
  - 清理误导性的 raw content 分支
- 在 worker 侧增加对象存储下载逻辑

交付物：

- 上传文件 -> 索引任务 -> chunk 入库 的主链
- 可观察的 job 状态

验收标准：

- 上传 `.txt` / `.md` / `.pdf` 后，`document_chunk` 有新增记录
- 索引失败时能看到 job 失败状态和错误信息

依赖：

- Task 4.2

---

### Task 4.4：接通任务执行前的 RAG 检索注入

优先级：`P0`

目标：
让 worker 在执行 Task 前真实使用项目上下文。

当前实现锚点：

- `worker/main.py` 目前只读取 `Task.goal` 后直接启动 Agent
- `worker/rag/retriever.py` 已可按 `project_id + query` 做检索
- `Agent.run()` 只接受 `goal` 和单个 `system_prompt`

解决方案：

1. 在 worker 执行 TaskRun 前先做 retrieval
2. 以 `task.goal` 为 query，`task.project_id` 为过滤条件
3. 把检索到的 chunk 格式化成上下文块，拼接进最终 `system_prompt`
4. 不改 Agent 主协议，先在 `worker/main.py` 这一层完成 context 注入
5. 把命中的 chunk 元信息写入 `TaskRun.working_memory`

具体改动：

- 修改 `worker/main.py`
  - agent run 前新增 `retrieve_project_context(...)`
  - 把 skill prompt 和 rag context 合并成最终 system prompt
- 复用 `worker/rag/retriever.py`
- 视情况新增 context formatter
  - 可放在 `worker/rag/context_builder.py`

交付物：

- goal -> retrieve -> context inject 主链
- 检索结果记录

验收标准：

- worker 执行任务时会基于 `project_id` 检索 chunk
- 检索结果会进入 Agent 上下文
- `TaskRun.working_memory` 可看到本次检索摘要或命中信息

依赖：

- Task 4.3

---

### Task 4.5：整理 `DocumentChunk.project_id` 类型与数据流

优先级：`P1`

目标：
消除 `DocumentChunk.project_id` 与主业务 UUID 体系的不一致。

当前实现锚点：

- `backend/app/models/document_chunk.py` 中 `project_id` 是 `String(255)`
- 其他主业务实体基本使用 `uuid.UUID`
- 现在各层只能不断做 `UUID <-> str` 转换

解决方案：

1. 长期正确解法是把 `DocumentChunk.project_id` 改成 UUID
2. 通过 Alembic migration 做类型迁移
3. 在迁移完成前，临时转换只允许集中在 service 层，不允许散在 router / worker / rag 文件各处

具体改动：

- 修改 `backend/app/models/document_chunk.py`
  - `project_id` 改为 UUID
- 新增 Alembic migration
  - 使用 `USING project_id::uuid`
- 修改以下调用方
  - `backend/app/routers/rag.py`
  - `backend/app/services/rag_service.py`
  - `worker/rag/indexer.py`
  - `worker/rag/retriever.py`

交付物：

- 一致的 project_id 类型策略
- 迁移脚本

验收标准：

- RAG 主链不再在多个地方散落 `str(project_id)` 这类兼容逻辑
- `DocumentChunk.project_id` 与主业务实体类型一致

依赖：

- Task 4.4

---

### Task 4.6：第二阶段抽取共享 RAG 包

优先级：`P2`

目标：
在 RAG 主链已经稳定后，再把单一实现真正抽成共享包。

当前实现锚点：

- 仓库已有 `shared/` 目录，但不是可直接安装的 Python 包
- `backend/pyproject.toml` 和 `worker/pyproject.toml` 各自独立
- backend / worker 运行时默认不会自动 import 仓库根目录下的共享代码

解决方案：

1. 不要直接把代码丢进 `shared/` 然后假设两边都能 import
2. 为 `shared` 新增自己的 `pyproject.toml`
3. backend 与 worker 通过本地 path dependency 安装 shared 包
4. 迁移顺序：
   - 先复制 `worker/rag` 基线实现到 `shared/rag`
   - 再切 backend / worker 导入
   - 最后删除 `worker/rag` 或仅保留薄包装

具体改动：

- 新增：
  - `shared/pyproject.toml`
  - `shared/rag/*`
- 修改：
  - `backend/pyproject.toml`
  - `worker/pyproject.toml`
- 调整 import 路径
  - backend / worker 都改为 import `shared.rag`

交付物：

- 可安装的 shared RAG 包
- backend / worker 统一 import 路径

验收标准：

- backend 和 worker 都能稳定 import `shared.rag`
- 仓库中不再维护两份核心 RAG 实现

依赖：

- Task 4.4
- Task 4.5

---

## Phase 5：Frontend 业务页面补齐

### Task 5.1：补项目详情页并接入文件组件

优先级：`P1`

目标：
把现有的项目卡片跳转变成真实可用页面。

当前实现锚点：

- `frontend/src/features/projects/components/ProjectCard.tsx` 跳转到 `/projects/{id}`
- `frontend/src/app/projects/[id]/page.tsx` 不存在
- `FileUploadZone` 和 `FileList` 已存在，但没有挂载页

解决方案：

1. 新增 `/projects/[id]` 页面
2. 页面直接复用现有文件上传和文件列表组件
3. 页面同时展示：
   - 项目基础信息
   - 文件上传区
   - 文件列表
   - 后续进入 conversation/task 的入口链接

具体改动：

- 新增 `frontend/src/app/projects/[id]/page.tsx`
- 复用：
  - `frontend/src/features/projects/components/FileUploadZone.tsx`
  - `frontend/src/features/projects/components/FileList.tsx`
- 如有缺口，新增获取单项目详情 API/hook

交付物：

- 可访问的 `/projects/{id}` 页面
- 文件上传与列表可用

验收标准：

- 项目卡片点击后不再 404
- 上传文件后页面能刷新显示文件列表

依赖：

- Task 4.3

---

### Task 5.2：补对话与任务创建页面

优先级：`P1`

目标：
让前端能够走通 `Conversation -> Message -> Task -> Run` 这条显式业务链。

当前实现锚点：

- backend 已有 `Conversation` / `Message` / `Task` / `TaskRun` API
- frontend 只有任务查看组件，没有对话页和任务创建页
- backend 当前没有“发消息自动创建任务”的聚合接口
- backend 当前也没有“技能列表 / 模型列表”的元数据 API

解决方案：

1. 不在这一步发明新的聚合后端接口
2. 前端按当前后端真实资源模型显式走四步：
   - 创建 Conversation
   - 创建 Message
   - 创建 Task
   - 创建 Run
3. skill/model 先采用“当前仓库静态选项 + 可编辑输入”
   - skill 可先对齐当前 `worker/skills/*`
   - model 可先用文本输入或固定常量
4. 后续若要做元数据接口，再单独开任务，不塞进本轮主链

具体改动：

- 新增：
  - `frontend/src/app/conversations/[id]/page.tsx`
  - `frontend/src/features/conversations/*`
- 扩展：
  - `frontend/src/features/tasks/*`
- 新增前端 API/hooks：
  - list/create conversations
  - list/create messages
  - create task
  - create run

交付物：

- 对话页
- 任务创建页
- 显式创建 Run 的 UI

验收标准：

- 用户可以从 UI 走通 `Conversation -> Task -> Run`
- 整个流程只依赖当前已存在或本轮新增的真实 API

依赖：

- Task 2.1
- Task 2.3

---

### Task 5.3：补 Run 详情页与实时执行展示

优先级：`P1`

目标：
把已有 `TaskRunViewer` 真实挂到路由页面。

当前实现锚点：

- `frontend/src/features/tasks/components/TaskRunViewer.tsx` 已存在
- `frontend/src/features/tasks/components/ExecutionTimeline.tsx` 已存在
- 当前没有 `/runs/[id]` 页面
- 事件类型尚未覆盖 `run_started / run_completed / artifact_created`

解决方案：

1. 新增 `/runs/[id]` 页面，统一加载：
   - run detail
   - websocket 事件流
2. 页面首次加载时用 HTTP 取当前状态
3. 有 `TaskRun.logs` 后，以历史日志初始化时间线，再追加 websocket 增量事件
4. 前端事件 union 类型扩展为真实主链事件集合

具体改动：

- 新增 `frontend/src/app/runs/[id]/page.tsx`
- 修改：
  - `frontend/src/features/tasks/components/TaskRunViewer.tsx`
  - `frontend/src/features/tasks/components/ExecutionTimeline.tsx`
  - `frontend/src/features/tasks/types.ts`
  - `frontend/src/features/tasks/hooks/useTaskRun.ts`
  - `frontend/src/features/tasks/hooks/useTaskRunStream.ts`

交付物：

- Run 详情页
- 实时执行时间线

验收标准：

- 运行任务时，可在页面看到 step / tool / result / artifact / completion 事件
- 刷新页面后仍能看到当前 run 状态，若已实现 logs，则能看到部分历史轨迹

依赖：

- Task 3.1
- Task 2.3

---

### Task 5.4：补 Artifact 与项目文件管理页

优先级：`P2`

目标：
让前端能查看 Artifact、下载 Artifact、保存 Artifact 到项目。

当前实现锚点：

- backend `artifacts.py` 只有 get/upload/download/delete
- backend 没有按项目或按 run 列表查询 Artifact 的接口
- frontend 没有 Artifact 相关页面

解决方案：

1. 先补 backend 列表接口，再做前端页
2. Artifact 页面最少支持：
   - 按项目查看
   - 按 run 查看
   - 下载
   - save-to-project
3. 保存到项目动作直接复用 Task 3.3 新增接口

具体改动：

- 修改 `backend/app/routers/artifacts.py`
  - 新增 `GET /api/projects/{project_id}/artifacts`
  - 可选新增 `GET /api/runs/{run_id}/artifacts`
- 新增：
  - `frontend/src/features/artifacts/*`
  - `frontend/src/app/projects/[id]/artifacts/page.tsx`

交付物：

- Artifact 列表页
- 下载和保存操作

验收标准：

- 用户可以从 UI 查看和下载 Artifact
- 用户可以从 UI 触发 save-to-project

依赖：

- Task 3.2
- Task 3.3

---

## Phase 6：基础设施与交付收尾

### Task 6.1：扩展 docker-compose 为全栈开发环境

优先级：`P2`

目标：
让 `docker-compose` 至少覆盖真实开发主场景，而不是只起依赖。

当前实现锚点：

- `docker-compose.yml` 当前只起：
  - postgres
  - redis
  - minio
- `README.md` 却写成 `docker-compose up -d` 后前后端可访问
- worker 如果容器化运行，还需要能访问宿主 Docker 去创建 sandbox

解决方案：

1. compose 新增：
   - `backend`
   - `worker`
   - `frontend`
2. worker 容器如果参与本地开发 compose，需要挂载：
   - Docker socket
   - 代码目录
3. 增加基础健康检查和启动顺序
4. 把 `badgers-sandbox:latest` 的构建方式写进 compose 或 README
5. Redis 在 compose 里保留，但说明当前不是主调度链

具体改动：

- 修改 `docker-compose.yml`
  - 新增 backend / worker / frontend services
  - worker 挂 `/var/run/docker.sock`
  - 加入需要的 environment
- 修改 `README.md`
  - 改成真实的一键启动说明
- 如有必要，补 sandbox image build 脚本或 compose build 配置

交付物：

- 接近一键启动的开发环境
- 与实际架构一致的 compose 说明

验收标准：

- 新开发者按 README 能启动完整栈
- compose 描述不再与真实可访问服务冲突

依赖：

- Task 2.2
- Task 3.1
- Task 4.3

---

### Task 6.2：收尾文档与交付验证

优先级：`P2`

目标：
让 README、架构文档、测试说明与真实系统行为一致。

当前实现锚点：

- README 当前存在多处失真：
  - 写的是 Redis queue 主链，但代码是 DB polling
  - 写的是 `/api/v1/*`，代码实际是 `/api/*`
  - 写的是 `docker-compose up` 后前后端可用，但 compose 实际没有这些服务
- 当前架构文档已经新增，但还需要随主链改造同步收口

解决方案：

1. 在所有核心任务完成后做一次文档回扫
2. 优先修正与代码冲突的硬事实：
   - API path
   - 调度方式
   - compose 能力
   - 配置命名
   - 当前 frontend 页面覆盖范围
3. 给出最终验收步骤，而不是只给散落命令

具体改动：

- 修改：
  - `README.md`
  - `docs/current-system-architecture.md`
  - `docs/target-architecture-gap-analysis.md`
  - `docs/rag-refactor-plan.md`
  - `docs/architecture-execution-task-list.md`
  - `docs/testing-guidelines.md`
- 新增最终联调验证清单：
  - 创建项目
  - 上传文件
  - 创建 conversation
  - 创建 task
  - 创建 run
  - 观察事件流
  - 下载 artifact
  - save-to-project
  - 触发 RAG 检索

交付物：

- 与真实行为一致的文档
- 最终交付验证步骤

验收标准：

- 文档中不再描述与代码明显冲突的行为
- 团队成员可按最终清单完成一次端到端验证

依赖：

- 全部核心任务完成后执行

---

## 6. 推荐执行批次

### 批次 A：必须先做

- Task 0.1
- Task 0.2
- Task 1.1
- Task 1.2
- Task 2.1
- Task 2.2

结果：

- worker 主链协议收口
- Task / Run 资源边界闭环
- 文档和代码不再对调度方式说两套话

### 批次 B：让系统“看得见”

- Task 2.3
- Task 3.1
- Task 3.2
- Task 3.3

结果：

- 用户能看到执行过程
- 执行结果能进入 Artifact 和项目文件体系

### 批次 C：把 RAG 变成系统能力

- Task 4.1
- Task 4.2
- Task 4.3
- Task 4.4
- Task 4.5

结果：

- 上传文件后可被索引
- 执行任务时能检索项目上下文

### 批次 D：补齐前端体验

- Task 5.1
- Task 5.2
- Task 5.3
- Task 5.4

结果：

- 前端可走完整业务链

### 批次 E：收尾

- Task 4.6
- Task 6.1
- Task 6.2

结果：

- 共享包整理
- 开发环境完整
- 文档与交付一致

---

## 7. 一句话执行建议

当前仓库最合理的推进顺序不是“继续往上叠功能”，而是：

**先统一 worker 模型和工具协议，接着打通 TaskRun 生命周期，再补 worker->backend 事件链和 Artifact 自动产出，随后把 RAG 统一到单一实现并接入上传与执行主链，最后再把前端页面和开发环境补齐。**

---

## 8. 批次 A 详细实施方案

本节把“批次 A”继续拆成可以直接开工的实施顺序。

原则：

1. 每一步都尽量保持可运行
2. 每一步结束后都能做局部验证
3. 不在同一步里同时处理两个不同层面的不确定性

建议顺序：

```text
A1 配置统一
  ->
A2 backend 测试基线收口
  ->
A3 模型协议统一
  ->
A4 工具协议统一
  ->
A5 TaskRun 生命周期闭环
  ->
A6 调度基线文档与代码收口
```

### A1：先做配置统一（对应 Task 0.1）

目的：
先消除“同一个系统两套配置名、三套默认值”的问题，避免后续每改一步都被配置噪音干扰。

实施步骤：

1. 先改 backend 配置层
   - 修改 `backend/app/config.py`
   - 把 `minio_*` 改为 `s3_*`
   - 默认值对齐当前 `.env.example` 的开发环境组合
2. 再改 backend 存储服务
   - 修改 `backend/app/services/storage.py`
   - 改读 `settings.s3_*`
   - 明确 endpoint 不带 `http://`
3. 再补 worker 配置
   - 修改 `worker/config.py`
   - 新增 `s3_*`
   - 新增 `embedding_model`
   - 为后续 RAG/Artifact 预留配置入口
4. 最后统一文档和样例
   - 修改 `.env.example`
   - 修改 `README.md`
   - 修改 `docker-compose.yml`

这一步不要做的事：

- 不要顺手开始改 RAG 代码
- 不要顺手做 compose 全栈化
- 不要在这一步引入兼容两套命名的复杂适配层，除非确实有启动依赖

完成定义：

- backend 本地配置来源清晰
- worker 本地配置来源清晰
- `.env.example` 可以作为唯一参考模板

建议局部验证：

1. 检查 backend 启动时能初始化 `StorageService`
2. 检查 worker 能读到新增配置字段
3. 人工核对 README 配置段是否与代码字段同名

建议提交边界：

- 一个提交只包含配置与文档收口，不夹带业务逻辑修改

---

### A2：收口 backend 测试基线（对应 Task 0.2）

目的：
把后续 backend 改造的回归验证从“不稳定 + 强依赖本机 PostgreSQL”变成“默认可跑一层，集成测试显式控制”。

实施步骤：

1. 重构 `backend/tests/conftest.py`
   - 去掉无条件 `init_db()`
   - 增加 unit client fixture
   - 增加 integration fixture
2. 先挑最简单的 router 测试转成 unit/contract 风格
   - 优先 `test_api_projects.py`
   - 然后 `test_api_tasks.py`
   - 再是 `test_api_runs.py`
3. 为 integration 测试加显式前提
   - 读取 `TEST_DATABASE_URL`
   - 未提供时 skip
4. 更新 `docs/testing-guidelines.md`
   - 写清楚默认跑什么
   - 写清楚什么时候需要 PostgreSQL + pgvector

这一步的关键取舍：

- 不追求一次把所有 backend 测试都改完
- 先建立规则，再逐个迁移
- RAG/vector 相关测试先保留在 integration 层

优先改动文件：

- `backend/tests/conftest.py`
- `backend/tests/test_api_projects.py`
- `backend/tests/test_api_tasks.py`
- `backend/tests/test_api_runs.py`
- `docs/testing-guidelines.md`

完成定义：

- 默认能跑一组 backend API 测试而不连接真实 PostgreSQL
- integration 失败不会表现成“本地端口拒绝连接”

建议局部验证：

1. 跑 unit/contract 测试子集
2. 在未提供 `TEST_DATABASE_URL` 时确认 integration 被 skip

建议提交边界：

- 单独一个提交处理测试基线，不与业务代码混改

---

### A3：统一模型协议（对应 Task 1.1）

目的：
先修掉 worker 主链最直接的协议断裂，让 `Agent` 和 `factory` 真正接上。

实施步骤：

1. 先切工厂出口
   - 修改 `worker/models/factory.py`
   - 返回 `openai_compat.OpenAIProvider`
   - 返回 `anthropic_native.AnthropicProvider`
2. 再统一 provider 构造参数
   - 修改 `worker/models/openai_compat.py`
   - 修改 `worker/models/anthropic_native.py`
   - 让它们都适配当前 `settings`
3. 再缩减旧 provider 的主链作用
   - `worker/models/openai_provider.py`
   - `worker/models/anthropic_provider.py`
   - `worker/models/base.py`
4. 最后补测试
   - 更新 `worker/tests/test_models_factory.py`
   - 更新/新增 `chat_completion` 风格测试
   - 回归 `worker/tests/test_agent.py`

这一步不要做的事：

- 不要同时改工具协议
- 不要同时引入新的模型路由能力
- 不要在这一步扩展新的 provider 类型

优先改动文件：

- `worker/models/factory.py`
- `worker/models/openai_compat.py`
- `worker/models/anthropic_native.py`
- `worker/tests/test_models_factory.py`
- `worker/tests/test_agent.py`

完成定义：

- `create_model_provider()` 的返回对象能被 `Agent` 直接消费
- `Agent.run()` 不再依赖“正好拿到兼容 provider”的偶然行为

建议局部验证：

1. 跑 `worker/tests/test_models_factory.py`
2. 跑 `worker/tests/test_agent.py`

建议提交边界：

- 一个提交专门处理模型协议，不和工具协议混在一起

---

### A4：统一工具协议（对应 Task 1.2）

目的：
把 worker 的第二个主链断点补上，让 Agent 能稳定调用全套工具，尤其是文件工具。

实施步骤：

1. 先扩展统一的 `ToolResult`
   - 修改 `worker/tools/tool_base.py`
   - 增加 `metadata`
   - 保持 `success/output/error` 为主返回面
2. 再把 PythonTool 改到新协议
   - 修改 `worker/tools/python.py`
3. 再把 WebFetchTool 改到新协议
   - 修改 `worker/tools/web.py`
4. 再把 BrowserTool 改到新协议
   - 修改 `worker/tools/browser.py`
5. 最后注册文件工具
   - 修改 `worker/tools/__init__.py`
   - 加入 `FileListTool` / `FileReadTool` / `FileWriteTool`
6. 必要时删除或弱化 `worker/tools/base.py`

推荐原因：

- PythonTool 和 WebFetchTool 改造面相对集中，先处理更容易收口
- BrowserTool 逻辑最长，放后面单独处理
- 文件工具本身已经走统一协议，最后接入最稳

优先改动文件：

- `worker/tools/tool_base.py`
- `worker/tools/python.py`
- `worker/tools/web.py`
- `worker/tools/browser.py`
- `worker/tools/__init__.py`
- `worker/tests/test_tools.py`
- `worker/tests/test_python_tool.py`
- `worker/tests/test_web_tool.py`
- `worker/tests/test_browser_tools.py`
- `worker/tests/test_agent.py`

完成定义：

- `get_all_tools()` 返回值全都能被 Agent 直接消费
- 文件工具已经进入默认工具集

建议局部验证：

1. 跑工具相关测试
2. 跑 `worker/tests/test_agent.py`

建议提交边界：

- 一个提交专门收口工具协议

---

### A5：打通 TaskRun 生命周期（对应 Task 2.1）

目的：
把 backend 的资源状态和 worker 的执行状态真正闭环。

实施步骤：

1. 先修 backend 创建 run 逻辑
   - 修改 `backend/app/routers/tasks.py`
   - 创建 `TaskRun` 后回写 `Task.current_run_id`
2. 再修 cancel 逻辑
   - 修改 `backend/app/routers/runs.py`
   - 取消时清理 `Task.current_run_id`
3. 再修 worker claim/finalize 逻辑
   - 修改 `worker/main.py`
   - claim 后更新 running 状态与时间
   - 完成/失败后清理 Task 指针
4. 最后补测试
   - backend 增加 run/task 状态相关测试
   - worker 增加成功/失败/取消分支测试

这一步的关键点：

- backend 和 worker 都会写 `TaskRun`，所以必须统一状态规则
- 不要先做复杂重试队列
- 先把“单个 Task 当前只有一个活动 Run”这件事钉死

优先改动文件：

- `backend/app/routers/tasks.py`
- `backend/app/routers/runs.py`
- `backend/app/models/task.py`
- `backend/app/schemas/task.py`
- `worker/main.py`
- `backend/tests/test_api_tasks.py`
- `backend/tests/test_api_runs.py`
- `worker/tests/test_main.py`

完成定义：

- 创建 run 后 Task 能立即读到 `current_run_id`
- run 终态后该指针被清理
- worker claim/finish/fail 路径不会留下脏状态

建议局部验证：

1. API 测试验证 create run / cancel run
2. worker 测试验证 success / failure 状态更新

建议提交边界：

- 一个提交专门处理 TaskRun 生命周期

---

### A6：固化当前调度基线（对应 Task 2.2）

目的：
在生命周期闭环后，把当前“DB polling 就是主链”的事实彻底写进代码结构和文档。

实施步骤：

1. 重构 `worker/main.py`
   - 提取 claim/scheduler 辅助函数
   - 明确“当前调度基线”为 DB polling
2. 回扫 README
   - 改掉 Redis queue 主链叙述
   - 改掉 `/api/v1` 错误路径描述
3. 回扫当前架构文档
   - `docs/current-system-architecture.md`
   - `docs/target-architecture-gap-analysis.md`
   - 保持与现状一致

这一步不要做的事：

- 不要此时切 Redis queue
- 不要把 compose 全栈化和调度基线收口混在一起

优先改动文件：

- `worker/main.py`
- `README.md`
- `docs/current-system-architecture.md`
- `docs/target-architecture-gap-analysis.md`

完成定义：

- 代码、README、架构文档都明确“当前是 DB polling”
- 不再出现“代码轮询 DB，文档却写 Redis 是当前主链”的冲突

建议局部验证：

1. 人工检查 README 架构图和描述
2. 人工检查 worker 启动日志或代码注释是否清晰表达当前调度模式

建议提交边界：

- 一个提交专门做调度基线和文档收口

---

## 9. 批次 A 完成后的状态定义

如果批次 A 做完，系统应该达到下面这个状态：

1. worker 主链不存在模型协议和工具协议的结构性断裂
2. `Task` 与 `TaskRun` 的关系真正可用，`current_run_id` 可被前端消费
3. backend 测试不再默认依赖真实 PostgreSQL 才能开始改造
4. 文档不再错误宣称 Redis queue 已经是当前主链

这时才能低风险进入下一批：

- 批次 B：事件流与 Artifact
- 批次 C：RAG 接主链

如果批次 A 没做完，就直接推进批次 B/C，会遇到两个问题：

1. worker 主链本身还没收口，事件和 RAG 接进去也不稳定
2. 回归验证基线不稳定，后续每一步都难确认是否真的改对

---

## 10. 下一步建议

如果按最小风险继续推进，下一步就不应该再补文档概念，而应该开始真正编码，顺序建议如下：

1. 先做 Task 0.1
2. 再做 Task 1.1
3. 再做 Task 1.2
4. 然后做 Task 2.1
5. 最后收口 Task 2.2

原因：

- 配置统一是所有后续步骤的底板
- 模型协议和工具协议修完之后，worker 主链才值得继续补生命周期
- 生命周期闭环后，文档和调度说明才能一次性收口
