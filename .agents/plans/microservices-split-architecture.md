# Feature: Microservices Architecture Split

将当前单体Backend拆分为4个独立的微服务，实现业务域隔离、独立部署和扩展。

## Feature Description

将Badgers MVP的单体Backend应用拆分为基于业务域的微服务架构：
- **Project Service**: 项目管理和对话管理
- **Task Service**: 任务管理、运行管理和产物管理（包含TaskRun Worker代码）
- **RAG Service**: 文档索引和检索服务（包含IndexJob Worker代码）
- **Storage Service**: 对象存储统一接口

每个服务独立部署、独立扩展，通过HTTP/gRPC进行同步通信，通过RabbitMQ进行异步通信。

## User Story

As a system architect
I want to split the monolithic backend into domain-based microservices
So that each service can be developed, deployed, and scaled independently, improving system maintainability and scalability

## Problem Statement

当前单体Backend存在以下问题：
1. **扩展困难**: 所有功能在一个服务中，无法针对特定功能独立扩展
2. **部署风险**: 任何改动都需要重新部署整个Backend，风险高
3. **团队协作**: 多人修改同一代码库容易产生冲突
4. **技术栈限制**: 所有功能必须使用相同的技术栈
5. **故障影响**: 一个模块的问题可能影响整个系统

## Solution Statement

采用渐进式微服务拆分策略：
1. 按业务域划分服务边界（Project、Task、RAG、Storage）
2. 每个服务独立代码仓库、独立数据库
3. 服务间通过API Gateway统一入口
4. 同步调用使用HTTP/REST，异步任务使用RabbitMQ
5. 保持Worker代码与对应服务在同一仓库，部署时可选择合并或分开

## Feature Metadata

**Feature Type**: Refactor/Architecture
**Estimated Complexity**: High
**Primary Systems Affected**:
- Backend (完全重构)
- Docker Compose (新增多个服务)
- 数据库 (拆分为多个独立数据库)
- API路由 (通过Gateway统一)

**Dependencies**:
- Nginx (API Gateway)
- 现有的FastAPI、SQLAlchemy、RabbitMQ

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**当前Backend结构**:
- `backend/app/main.py` - 当前单体应用入口，包含所有router注册
- `backend/app/routers/projects.py` - 项目管理API
- `backend/app/routers/conversations.py` - 对话管理API
- `backend/app/routers/tasks.py` - 任务管理API
- `backend/app/routers/runs.py` - 运行管理API
- `backend/app/routers/artifacts.py` - 产物管理API
- `backend/app/routers/rag.py` - RAG相关API
- `backend/app/models/` - 所有数据模型
- `backend/app/schemas/` - 所有Pydantic schemas
- `backend/app/services/` - 业务逻辑服务
- `docker-compose.yml` - 当前部署配置

**Worker代码**:
- `worker/main.py` - Worker主循环和执行逻辑
- `worker/worker_taskrun.py` - TaskRun Worker入口
- `worker/worker_indexjob.py` - IndexJob Worker入口

### New Files/Directories to Create

**新服务目录结构**:
```
services/
├── project-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── Dockerfile
│   └── pyproject.toml
├── task-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── worker/
│   │   └── taskrun_worker.py
│   ├── Dockerfile
│   └── pyproject.toml
├── rag-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── worker/
│   │   └── indexjob_worker.py
│   ├── Dockerfile
│   └── pyproject.toml
└── storage-service/
    ├── app/
    │   ├── main.py
    │   └── services/
    ├── Dockerfile
    └── pyproject.toml
```

**API Gateway配置**:
- `nginx/nginx.conf` - Nginx配置文件
- `nginx/Dockerfile` - Nginx容器配置

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
  - Specific section: Multiple Applications, Sub Applications
  - Why: 理解如何拆分FastAPI应用
- [Microservices Patterns](https://microservices.io/patterns/index.html)
  - Specific section: API Gateway, Database per Service
  - Why: 微服务架构最佳实践
- [Nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
  - Why: 配置API Gateway


### Patterns to Follow

**FastAPI Application Pattern** (from `backend/app/main.py`):
```python
app = FastAPI(title="Service Name")

@app.on_event("startup")
async def startup_event():
    # Initialize connections

app.include_router(router)
```

**Database Session Pattern** (from `backend/app/database.py`):
```python
async def get_db():
    async with async_session_maker() as session:
        yield session
```

**Router Pattern** (from `backend/app/routers/`):
```python
router = APIRouter(prefix="/api/resource", tags=["resource"])

@router.get("/")
async def list_resources(db: AsyncSession = Depends(get_db)):
    # Implementation
```

**Logging Pattern** (from `backend/app/routers/projects.py:16`):
```python
import structlog
logger = structlog.get_logger()
logger.info("event_name", key=value)
```

---

## IMPLEMENTATION PLAN

### Phase 1: 准备工作（不影响现有系统）

创建新的服务目录结构，设置基础配置，但不修改现有Backend。

**Tasks:**
- 创建services目录和各服务子目录
- 配置各服务的pyproject.toml
- 设置Docker构建文件
- 配置Nginx API Gateway

### Phase 2: 拆分第一个服务（Storage Service）

从最简单、最独立的服务开始，验证拆分流程。

**Tasks:**
- 提取Storage Service代码
- 配置独立部署
- 修改Backend调用Storage Service
- 测试验证

### Phase 3: 拆分RAG Service

拆分RAG相关功能，包含IndexJob Worker。

**Tasks:**
- 提取RAG API和Worker代码
- 配置独立数据库
- 修改Backend调用RAG Service
- 测试验证

### Phase 4: 拆分Task Service

拆分任务管理功能，包含TaskRun Worker。

**Tasks:**
- 提取Task API和Worker代码
- 配置独立数据库
- 修改其他服务调用Task Service
- 测试验证

### Phase 5: 拆分Project Service

拆分项目和对话管理功能。

**Tasks:**
- 提取Project和Conversation API
- 配置独立数据库
- 配置API Gateway路由
- 测试验证

### Phase 6: 清理和优化

移除旧Backend，优化服务间通信。

**Tasks:**
- 移除旧backend目录
- 优化API Gateway配置
- 添加服务监控
- 性能测试

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Phase 1: 准备工作

### Task 1.1: CREATE services/ directory structure

- **CREATE**: 新的services目录和子目录
- **IMPLEMENTATION**:
  ```bash
  mkdir -p services/project-service/app/{routers,models,schemas,services}
  mkdir -p services/task-service/app/{routers,models,schemas,services}
  mkdir -p services/task-service/worker
  mkdir -p services/rag-service/app/{routers,models,schemas,services}
  mkdir -p services/rag-service/worker
  mkdir -p services/storage-service/app/services
  mkdir -p nginx
  ```
- **VALIDATE**: `ls -la services/`

### Task 1.2: CREATE services/storage-service/pyproject.toml

- **CREATE**: Storage Service依赖配置
- **PATTERN**: 复制backend/pyproject.toml，简化依赖
- **IMPLEMENTATION**:
  ```toml
  [project]
  name = "storage-service"
  version = "0.1.0"
  requires-python = ">=3.11"
  dependencies = [
      "fastapi>=0.110.0",
      "uvicorn[standard]>=0.27.0",
      "minio>=7.2.0",
      "structlog>=24.1.0",
      "httpx>=0.26.0",
  ]
  ```
- **VALIDATE**: `cd services/storage-service && uv sync`

### Task 1.3: CREATE services/storage-service/Dockerfile

- **CREATE**: Storage Service容器配置
- **PATTERN**: 复制backend/Dockerfile结构
- **IMPLEMENTATION**:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY pyproject.toml ./
  RUN pip install uv && uv sync
  COPY app/ ./app/
  CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- **VALIDATE**: `docker build -t storage-service services/storage-service/`

### Task 1.4: CREATE nginx/nginx.conf

- **CREATE**: API Gateway配置
- **IMPLEMENTATION**:
  ```nginx
  upstream project_service {
      server project-service:8000;
  }
  upstream task_service {
      server task-service:8000;
  }
  upstream rag_service {
      server rag-service:8000;
  }
  upstream storage_service {
      server storage-service:8000;
  }

  server {
      listen 80;

      location /api/projects {
          proxy_pass http://project_service;
      }
      location /api/conversations {
          proxy_pass http://project_service;
      }
      location /api/tasks {
          proxy_pass http://task_service;
      }
      location /api/runs {
          proxy_pass http://task_service;
      }
      location /api/artifacts {
          proxy_pass http://task_service;
      }
      location /api/rag {
          proxy_pass http://rag_service;
      }
      location /api/storage {
          proxy_pass http://storage_service;
      }
  }
  ```
- **VALIDATE**: `nginx -t -c nginx/nginx.conf`


### Phase 2: 拆分Storage Service

### Task 2.1: CREATE services/storage-service/app/main.py

- **CREATE**: Storage Service主应用
- **PATTERN**: 从backend/app/services/storage.py提取
- **IMPLEMENTATION**:
  ```python
  from fastapi import FastAPI, UploadFile, File
  from minio import Minio
  import structlog

  app = FastAPI(title="Storage Service")
  logger = structlog.get_logger()

  # MinIO client initialization
  minio_client = Minio(...)

  @app.post("/api/storage/upload")
  async def upload_file(file: UploadFile = File(...)):
      # Implementation from storage_service.upload_file
      pass

  @app.get("/api/storage/download/{object_name}")
  async def download_file(object_name: str):
      # Implementation from storage_service.download_file
      pass
  ```
- **GOTCHA**: 复用backend/app/services/storage.py的逻辑
- **VALIDATE**: `cd services/storage-service && uv run python -c "from app.main import app; print('OK')"`

### Task 2.2: UPDATE docker-compose.yml - Add storage-service

- **ADD**: Storage Service到compose配置
- **IMPLEMENTATION**:
  ```yaml
  storage-service:
    build:
      context: ./services/storage-service
    environment:
      S3_ENDPOINT: minio:9000
      S3_ACCESS_KEY: ${S3_ACCESS_KEY:-badgers}
      S3_SECRET_KEY: ${S3_SECRET_KEY:-badgers_dev_password}
    ports:
      - "8005:8000"
    depends_on:
      - minio
  ```
- **VALIDATE**: `docker compose config`

### Task 2.3: CREATE services/storage-service/app/client.py

- **CREATE**: Storage Service HTTP客户端（供其他服务调用）
- **IMPLEMENTATION**:
  ```python
  import httpx

  class StorageClient:
      def __init__(self, base_url: str):
          self.base_url = base_url
          self.client = httpx.AsyncClient()

      async def upload_file(self, file_path: str, content: bytes):
          response = await self.client.post(
              f"{self.base_url}/api/storage/upload",
              files={"file": content}
          )
          return response.json()
  ```
- **VALIDATE**: `cd services/storage-service && uv run python -c "from app.client import StorageClient; print('OK')"`


### Phase 3-6: 后续服务拆分（简化说明）

由于完整的微服务拆分是一个大型项目，后续阶段遵循相同模式：

**Phase 3: RAG Service**
- 提取 backend/app/routers/rag.py
- 提取 backend/rag/ 目录
- 包含 worker/worker_indexjob.py
- 独立数据库：document_chunks, document_index_jobs

**Phase 4: Task Service**
- 提取 backend/app/routers/tasks.py, runs.py, artifacts.py
- 包含 worker/worker_taskrun.py
- 独立数据库：tasks, task_runs, sandboxes, artifacts

**Phase 5: Project Service**
- 提取 backend/app/routers/projects.py, conversations.py
- 独立数据库：projects, project_nodes, conversations, messages

**Phase 6: 集成和优化**
- 配置 API Gateway
- 服务间通信优化
- 监控和日志聚合

---

## TESTING STRATEGY

### 服务独立测试
- 每个服务独立运行单元测试
- API端点测试
- 数据库操作测试

### 服务间集成测试
- 通过API Gateway访问各服务
- 跨服务调用测试
- 端到端业务流程测试

---

## VALIDATION COMMANDS

### Level 1: 服务启动验证
```bash
# 启动所有服务
docker compose up -d

# 检查服务健康
curl http://localhost/api/projects
curl http://localhost/api/tasks
curl http://localhost/api/rag
curl http://localhost/api/storage
```

### Level 2: 端到端测试
```bash
# 创建项目
curl -X POST http://localhost/api/projects -d '{"name": "test"}'

# 上传文件
curl -X POST http://localhost/api/projects/{id}/files/upload -F "file=@test.txt"

# 创建任务
curl -X POST http://localhost/api/tasks -d '{"goal": "test task"}'
```

---

## ACCEPTANCE CRITERIA

- [ ] 4个服务独立运行
- [ ] API Gateway正确路由请求
- [ ] 服务间通信正常
- [ ] 数据库独立且数据一致
- [ ] Worker正常执行任务
- [ ] 所有现有功能正常工作
- [ ] 性能无明显下降

---

## NOTES

### 实施建议

**渐进式迁移**：
1. 先完成RabbitMQ迁移（已有计划）
2. 再拆分Storage Service（最简单）
3. 逐步拆分其他服务
4. 最后移除旧Backend

**数据库策略**：
- 初期：共享数据库（简单）
- 后期：独立数据库（解耦）

**部署灵活性**：
- 开发环境：可以合并部署
- 生产环境：独立部署和扩展

### 预估工作量

- Phase 1-2: 1-2周
- Phase 3-4: 2-3周
- Phase 5-6: 1-2周
- **总计**: 4-7周

### 风险提示

- 服务间通信增加网络开销
- 分布式事务处理复杂
- 运维复杂度显著提升
- 需要团队具备微服务经验

**建议**: 先完成RabbitMQ迁移，验证业务稳定后再考虑微服务拆分。
