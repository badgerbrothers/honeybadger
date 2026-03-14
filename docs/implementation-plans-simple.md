# Badgers MVP 实施计划（简化版）

## Phase 1: Foundation（第 1-2 周）

### Plan 1.1: 项目基础结构搭建
创建完整的项目目录结构（backend/、worker/、frontend/、docker/），初始化配置文件（pyproject.toml、package.json、docker-compose.yml），设置开发环境。**2-3h**

### Plan 1.2: 数据库模式和模型
创建所有 SQLAlchemy 模型（Project、Conversation、Task、Run、Artifact 等），设置 Alembic 迁移。**3-4h**

### Plan 1.3: Pydantic Schemas
为所有资源创建 Create、Update、Response schemas，遵循 PRD 定义的边界。**2-3h**

### Plan 1.4: FastAPI 基础 API - Projects
实现 Project CRUD 端点，设置 FastAPI 应用、CORS、日志中间件。**3-4h**

### Plan 1.5: FastAPI 基础 API - Conversations & Tasks
实现 Conversation 和 Task 端点，确保边界清晰（Conversation 不直接创建 Task）。**3-4h**

### Plan 1.6: Docker 沙箱管理器基础
实现沙箱生命周期管理（创建、执行、销毁），创建基础 Docker 镜像。**4-5h**

### Plan 1.7: 基础代理编排器
实现简单的 Agent 执行循环，调用 LLM，执行基础文件工具。**4-5h**

### Plan 1.8: Next.js 前端基础结构
创建 Next.js 项目，实现项目列表和创建页面，配置 Tailwind 和 API 客户端。**4-5h**

---

## Phase 2: Tool System & Real-time Updates（第 3-4 周）

### Plan 2.1: 浏览器工具
使用 Playwright 实现 browser.open、click、type、extract、screenshot。**4-5h**

### Plan 2.2: Python 执行工具
实现 python.run 工具，在沙箱中执行 Python 代码，捕获 stdout/stderr。**3-4h**

### Plan 2.3: Web Fetch 工具
实现 web.fetch 工具，支持 GET/POST 请求，JSON 解析。**2-3h**

### Plan 2.4: Run API 和事件流
实现 Run 相关端点（GET /runs/{id}、POST /runs/{id}/cancel），设置 WebSocket 事件流。**4-5h**

### Plan 2.5: Artifact 管理
实现 Artifact 存储（MinIO）、下载、保存到项目功能。**3-4h**

### Plan 2.6: 前端实时更新
实现 WebSocket 客户端，显示任务执行进度和工具调用。**4-5h**

### Plan 2.7: 任务执行页面
创建任务详情页面，显示执行日志、步骤、工件列表。**3-4h**

---

## Phase 3: RAG, Memory & Skills（第 5-6 周）

### Plan 3.1: 文档解析器
实现 PDF、Markdown、TXT 解析器。**3-4h**

### Plan 3.2: pgvector 集成和 RAG
设置 pgvector，实现文档索引和相似度检索。**4-5h**

### Plan 3.3: 文件上传功能
实现项目文件上传 API 和前端界面。**2-3h**

### Plan 3.4: 记忆系统
实现对话摘要、项目记忆、任务 working memory。**4-5h**

### Plan 3.5: Skill 系统
实现 3 个 Skill 模板（research_report、webpage、file_analysis）。**3-4h**

### Plan 3.6: Skill 选择界面
在前端添加 Skill 选择功能。**2-3h**

---

## Phase 4: Model Abstraction & Polish（第 7-8 周）

### Plan 4.1: 统一模型接口
创建模型抽象层，支持 OpenAI-compatible 和 Anthropic。**4-5h**

### Plan 4.2: Embedding 提供商
实现 Embedding 模型抽象和配置。**2-3h**

### Plan 4.3: 模型配置和路由
实现默认模型配置、per-task 模型选择。**2-3h**

### Plan 4.4: 错误处理和重试
完善错误处理、任务重试逻辑。**3-4h**

### Plan 4.5: 项目文件浏览器
实现完整的项目文件浏览和管理界面。**4-5h**

### Plan 4.6: Docker Compose 完整配置
完善 docker-compose.yml，添加所有服务和配置。**2-3h**

### Plan 4.7: 文档和部署指南
编写完整的 README、部署文档、API 文档。**3-4h**

---

## Phase 5: Worker Integration & System Completion（第 9-10 周）

### Plan 5.1: Worker 主循环实现
创建 worker/main.py 入口文件，实现完整的任务执行流程：从 Redis 队列获取任务 → 创建沙箱 → 初始化 Agent → 执行任务 → 保存结果 → 清理沙箱。集成数据库操作（SandboxSession）和 WebSocket 事件广播。**5-6h**

---

**总计：** 约 125-156 小时（Phase 1: 25-32h, Phase 2: 23-30h, Phase 3: 18-24h, Phase 4: 20-26h, Phase 5: 5-6h）

**使用方法：** 按顺序执行每个 plan，使用 `/core_piv_loop:plan-feature` 创建详细计划，使用 `/core_piv_loop:execute` 执行。
