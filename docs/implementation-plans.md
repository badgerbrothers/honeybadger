# Badgers MVP 实施计划

## 文档说明

本文档将 Badgers MVP PRD 中定义的 4 个实施阶段分解为具体的、可执行的 plan。每个 plan 设计为 2-4 小时可完成的独立任务。

**使用方法：**
1. 按顺序执行每个 plan
2. 使用 `/core_piv_loop:plan-feature` 为每个 plan 创建详细实施计划
3. 使用 `/core_piv_loop:execute` 执行计划
4. 完成后使用 `/validation:validate` 验证
5. 使用 `/commit` 提交代码

---

## Phase 1: Foundation（第 1-2 周）

**阶段目标：** 建立核心基础设施和基本任务执行循环

### Plan 1.1: 项目基础结构搭建

**目标：** 创建完整的项目目录结构和开发环境配置

**任务描述：**
```
实施 Badgers MVP 项目基础结构和开发环境设置

创建内容：
1. 项目目录结构（backend/、worker/、frontend/、shared/、docker/）
2. 各子项目配置文件（pyproject.toml、package.json、tsconfig.json）
3. 开发环境配置（.env.example、.gitignore）
4. Docker Compose 配置（PostgreSQL、Redis、MinIO）
5. 基础 README 和开发文档
```

**交付物：**
- [ ] 完整的目录结构
- [ ] backend/pyproject.toml（FastAPI、SQLAlchemy、structlog 等依赖）
- [ ] worker/pyproject.toml（Docker SDK、Playwright 等依赖）
- [ ] frontend/package.json（Next.js、React、TypeScript 等依赖）
- [ ] docker-compose.yml（PostgreSQL、Redis、MinIO 服务）
- [ ] .env.example（所有环境变量模板）
- [ ] 更新后的 README.md（包含实际的启动命令）

**验证标准：**
- `docker-compose up -d` 成功启动所有服务
- `uv sync` 在 backend/ 和 worker/ 中成功安装依赖
- `npm install` 在 frontend/ 中成功安装依赖

**预计时间：** 2-3 小时

---

### Plan 1.2: 数据库模式和模型

**目标：** 创建 SQLAlchemy 模型和数据库迁移

**任务描述：**
```
实施 Badgers MVP 数据库模式

创建模型：
1. Project（项目）
2. ProjectNode（项目文件节点）
3. Conversation（对话）
4. Message（消息）
5. Task（任务）
6. TaskRun（任务运行）
7. SandboxSession（沙箱会话）
8. Artifact（工件）

设置：
- Alembic 迁移配置
- 数据库连接和会话管理
- 基础 PRAGMA 设置（如果使用 SQLite）或 PostgreSQL 配置
```

**交付物：**
- [ ] backend/app/models/ 目录下的所有模型文件
- [ ] backend/app/database.py（数据库连接）
- [ ] Alembic 配置和初始迁移
- [ ] 模型关系图文档

**验证标准：**
- `alembic upgrade head` 成功创建所有表
- 所有外键关系正确
- 可以创建和查询测试数据

**预计时间：** 3-4 小时

---

### Plan 1.3: Pydantic Schemas

**目标：** 创建所有 API 的请求/响应 schema

**任务描述：**
```
实施 Badgers MVP Pydantic Schemas

创建 schemas：
1. Project schemas（ProjectCreate、ProjectResponse）
2. Conversation schemas
3. Message schemas
4. Task schemas（TaskCreate、TaskResponse）
5. Run schemas（RunResponse）
6. Artifact schemas

遵循原则：
- 分离 Create、Update、Response schemas
- 使用 Pydantic v2 语法
- 添加字段验证和文档字符串
```

**交付物：**
- [ ] backend/app/schemas/ 目录下的所有 schema 文件
- [ ] 每个资源的 Create、Update、Response schemas
- [ ] Schema 文档

**验证标准：**
- 所有 schemas 可以正确序列化/反序列化
- 字段验证正常工作
- 类型提示完整

**预计时间：** 2-3 小时

---

### Plan 1.4: FastAPI 基础 API - Projects

**目标：** 实现 Project 相关的 CRUD API 端点

**任务描述：**
```
实施 Project API 端点

实现端点：
1. POST /api/v1/projects - 创建项目
2. GET /api/v1/projects/{id} - 获取项目详情
3. GET /api/v1/projects - 列出所有项目
4. GET /api/v1/projects/{id}/files - 列出项目文件
5. GET /api/v1/projects/{id}/nodes/{node_id}/content - 下载文件

设置：
- FastAPI 应用初始化
- CORS 中间件
- 请求日志中间件（structlog）
- 依赖注入（数据库会话）
```

**交付物：**
- [ ] backend/app/main.py（FastAPI 应用）
- [ ] backend/app/routers/projects.py（Project 路由）
- [ ] backend/app/dependencies.py（依赖注入）
- [ ] backend/app/logging_config.py（structlog 配置）
- [ ] 基础测试（pytest）

**验证标准：**
- `uvicorn app.main:app --reload` 成功启动
- 访问 http://localhost:8000/docs 可以看到 API 文档
- 可以通过 API 创建和查询项目
- 日志正确输出

**预计时间：** 3-4 小时


---

### Plan 1.5: FastAPI 基础 API - Conversations & Tasks

**目标：** 实现 Conversation 和 Task 相关的 API 端点

**任务描述：**
```
实施 Conversation 和 Task API 端点

Conversation 端点：
1. POST /api/v1/conversations - 创建对话
2. GET /api/v1/conversations/{id} - 获取对话详情
3. POST /api/v1/conversations/{id}/messages - 发送消息

Task 端点：
1. POST /api/v1/tasks - 创建任务
2. GET /api/v1/tasks/{id} - 获取任务详情
3. GET /api/v1/tasks/{id}/runs - 列出任务的所有运行
4. POST /api/v1/tasks/{id}/retry - 重试任务
```

**交付物：**
- [ ] backend/app/routers/conversations.py
- [ ] backend/app/routers/tasks.py
- [ ] 相关的服务层代码
- [ ] API 测试

**验证标准：**
- 所有端点返回正确的状态码和数据
- 边界清晰（Conversation 不直接创建 Task）
- Task API 只返回 task 级属性，不返回 run 状态

**预计时间：** 3-4 小时

---

### Plan 1.6: Docker 沙箱管理器基础

**目标：** 实现 Docker 沙箱的生命周期管理

**任务描述：**
```
实施 Docker 沙箱管理器

功能：
1. 创建沙箱（基于基础镜像）
2. 挂载工作目录
3. 启动容器
4. 执行命令
5. 停止和销毁容器
6. 资源限制（CPU、内存）

创建：
- 基础沙箱 Docker 镜像（Python + 常用库）
- SandboxManager 类
- 沙箱生命周期管理
```

**交付物：**
- [ ] worker/sandbox/manager.py（SandboxManager 类）
- [ ] worker/sandbox/docker_backend.py（Docker 操作）
- [ ] docker/sandbox-base/Dockerfile（基础镜像）
- [ ] 沙箱测试

**验证标准：**
- 可以成功创建和销毁沙箱
- 可以在沙箱中执行简单命令
- 资源限制生效
- 沙箱隔离正常工作

**预计时间：** 4-5 小时

---

### Plan 1.7: 基础代理编排器

**目标：** 实现简单的代理执行循环

**任务描述：**
```
实施基础代理编排器

功能：
1. 接收任务目标
2. 调用 LLM 生成计划
3. 执行简单的文件工具（file.write）
4. 返回结果
5. 记录执行日志

暂不实现：
- 复杂工具（浏览器、Python 执行）
- 多步骤迭代
- 错误重试
```

**交付物：**
- [ ] worker/orchestrator/agent.py（Agent 类）
- [ ] worker/orchestrator/executor.py（执行器）
- [ ] worker/tools/base.py（工具接口）
- [ ] worker/tools/file.py（文件工具）
- [ ] worker/models/base.py（模型接口基础）

**验证标准：**
- 可以接收任务并调用 LLM
- 可以执行 file.write 工具
- 执行日志正确记录
- 可以返回结果

**预计时间：** 4-5 小时

---

### Plan 1.8: Next.js 前端基础结构

**目标：** 创建 Next.js 项目基础和项目管理页面

**任务描述：**
```
实施 Next.js 前端基础

创建：
1. Next.js App Router 结构
2. Tailwind CSS 配置
3. API 客户端（基于 fetch）
4. 项目列表页面
5. 项目创建页面
6. 基础布局和导航

使用：
- TypeScript
- shadcn/ui 组件
- TanStack Query
```

**交付物：**
- [ ] frontend/src/app/ 目录结构
- [ ] frontend/src/lib/api-client.ts
- [ ] frontend/src/app/projects/page.tsx（项目列表）
- [ ] frontend/src/components/project-create-form.tsx
- [ ] Tailwind 和 shadcn/ui 配置

**验证标准：**
- `npm run dev` 成功启动
- 可以访问项目列表页面
- 可以创建新项目
- UI 响应式且美观

**预计时间：** 4-5 小时

---

## Phase 2: Tool System & Real-time Updates（第 3-4 周）

**阶段目标：** 实现完整工具套件和实时任务监控

### Plan 2.1: 浏览器工具实现

**目标：** 使用 Playwright 实现浏览器自动化工具

**任务描述：**
```
实施浏览器工具

实现工具：
1. browser.open - 打开 URL
2. browser.click - 点击元素
3. browser.type - 输入文本
4. browser.extract - 提取内容
5. browser.screenshot - 截图

功能：
- 自动等待页面加载
- 元素可见性检查
- 截图保存为 artifact
```

**交付物：**
- [ ] worker/tools/browser.py
- [ ] Playwright 配置
- [ ] 浏览器工具测试

**验证标准：**
- 可以打开网页并提取内容
- 截图正确保存
- 错误处理完善

**预计时间：** 4-5 小时
