# Feature: FastAPI 基础 API - Projects

## Feature Description

实现 Badgers MVP 的第一个完整 API 资源端点 - Projects API。包括 CRUD 操作（创建、读取、更新、删除项目），同时设置 FastAPI 应用的基础设施：CORS 中间件、结构化日志、错误处理和数据库集成。

## User Story

作为前端开发者
我想要通过 RESTful API 管理项目
以便我可以创建、查看、更新和删除项目，并为后续功能（对话、任务）奠定基础

## Problem Statement

当前 FastAPI 应用只有一个健康检查端点，缺少：
- 实际的业务 API 端点
- CORS 配置（前端无法调用）
- 结构化日志记录
- 统一的错误处理
- 数据库会话管理集成

## Solution Statement

实现 Projects API 作为第一个完整的资源端点：
1. 创建 `/api/projects` router 实现 CRUD 操作
2. 配置 CORS 允许前端跨域访问
3. 添加 structlog 中间件记录请求/响应
4. 实现统一的 HTTP 异常处理
5. 集成数据库会话依赖注入

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: Backend API Layer
**Dependencies**: FastAPI, SQLAlchemy, structlog

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**IMPORTANT: READ THESE BEFORE IMPLEMENTING!**

- `backend/app/main.py` - FastAPI 应用入口，需要添加 router 和中间件
- `backend/app/config.py` - 配置管理，可能需要添加 CORS 配置
- `backend/app/database.py` - 数据库连接和 get_db 依赖
- `backend/app/models/project.py` - Project 和 ProjectNode 模型
- `backend/app/schemas/project.py` - Project schemas（Create, Update, Response）
- `.claude/PRD.md` (Section 7.1) - Projects API 规范

### New Files to Create

- `backend/app/routers/projects.py` - Projects API 端点实现
- `backend/app/middleware/logging.py` - 结构化日志中间件（可选）
- `backend/tests/test_api_projects.py` - Projects API 集成测试

### Relevant Documentation

**YOU SHOULD READ THESE BEFORE IMPLEMENTING!**

- [FastAPI Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
  - APIRouter 使用模式
  - Why: 需要创建模块化的 router
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
  - CORSMiddleware 配置
  - Why: 前端需要跨域访问
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
  - 数据库会话依赖注入
  - Why: 每个端点需要数据库访问

### Patterns to Follow

**API Router Pattern:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.get("/")
async def list_projects(db: AsyncSession = Depends(get_db)):
    # Implementation
    pass
```

**CRUD Operations:**
- GET /api/projects - 列出所有项目
- POST /api/projects - 创建新项目
- GET /api/projects/{id} - 获取单个项目
- PATCH /api/projects/{id} - 更新项目
- DELETE /api/projects/{id} - 删除项目

**Error Handling:**
- 使用 HTTPException 返回标准错误
- 404 for not found
- 422 for validation errors (自动)
- 500 for server errors

---

## IMPLEMENTATION PLAN

### Phase 1: FastAPI 应用配置

设置 CORS、日志和错误处理基础设施。

**Tasks:**
- 更新 main.py 添加 CORS 中间件
- 配置 structlog（可选，使用 print 也可以）
- 添加全局异常处理器

### Phase 2: Projects Router 实现

实现 Projects CRUD 端点。

**Tasks:**
- 创建 projects.py router
- 实现 5 个 CRUD 端点
- 集成数据库会话依赖

### Phase 3: 测试

验证 API 端点功能。

**Tasks:**
- 创建集成测试
- 测试所有 CRUD 操作
- 测试错误场景

### Phase 4: 验证

运行所有验证命令确保质量。

**Tasks:**
- Linting 检查
- 测试覆盖率
- 手动 API 测试

---

## STEP-BY-STEP TASKS

### UPDATE backend/app/main.py

- **IMPLEMENT**: 添加 CORS 中间件配置
- **IMPLEMENT**: 注册 projects router
- **IMPORTS**: `from fastapi.middleware.cors import CORSMiddleware`
- **IMPORTS**: `from app.routers import projects`
- **PATTERN**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(projects.router)
```
- **VALIDATE**: `uv run python -c "from app.main import app; print('OK')"`

### CREATE backend/app/routers/projects.py

- **IMPLEMENT**: 创建 APIRouter 实例
- **IMPLEMENT**: 实现 5 个 CRUD 端点
- **IMPORTS**: `from fastapi import APIRouter, Depends, HTTPException`
- **IMPORTS**: `from sqlalchemy.ext.asyncio import AsyncSession`
- **IMPORTS**: `from sqlalchemy import select`
- **IMPORTS**: `from app.database import get_db`
- **IMPORTS**: `from app.models.project import Project`
- **IMPORTS**: `from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse`
- **ENDPOINTS**:
  - `GET /api/projects` - 列出所有项目
  - `POST /api/projects` - 创建项目
  - `GET /api/projects/{project_id}` - 获取单个项目
  - `PATCH /api/projects/{project_id}` - 更新项目
  - `DELETE /api/projects/{project_id}` - 删除项目
- **VALIDATE**: `uv run python -c "from app.routers.projects import router; print('OK')"`

### CREATE backend/tests/test_api_projects.py

- **IMPLEMENT**: 创建 pytest 测试用例
- **IMPLEMENT**: 测试所有 CRUD 操作
- **IMPORTS**: `import pytest`
- **IMPORTS**: `from httpx import AsyncClient`
- **IMPORTS**: `from app.main import app`
- **PATTERN**: 使用 pytest-asyncio 和 httpx AsyncClient
- **VALIDATE**: `uv run pytest backend/tests/test_api_projects.py -v`

---

## TESTING STRATEGY

### Integration Tests

使用 httpx AsyncClient 测试 API 端点：

**测试用例：**
- test_create_project - 创建项目成功
- test_list_projects - 列出所有项目
- test_get_project - 获取单个项目
- test_update_project - 更新项目
- test_delete_project - 删除项目
- test_get_nonexistent_project - 404 错误

### Edge Cases

- 创建项目时 name 为空字符串（应该失败）
- 获取不存在的项目 ID（404）
- 更新不存在的项目（404）
- 删除不存在的项目（404）

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd backend && uv run ruff check app/routers/ app/main.py
```

**Expected**: All checks passed

### Level 2: Import Validation

```bash
cd backend && uv run python -c "from app.main import app; from app.routers.projects import router; print('Imports OK')"
```

**Expected**: Imports OK

### Level 3: Unit Tests

```bash
cd backend && uv run pytest tests/test_api_projects.py -v
```

**Expected**: All tests pass

### Level 4: Manual API Testing

启动服务器并测试端点：

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

然后在另一个终端测试：

```bash
# 创建项目
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Project","description":"Test"}'

# 列出项目
curl http://localhost:8000/api/projects

# 获取项目
curl http://localhost:8000/api/projects/{project_id}
```

**Expected**: 正确的 JSON 响应

---

## ACCEPTANCE CRITERIA

- [ ] FastAPI 应用配置了 CORS 中间件
- [ ] Projects router 已创建并注册到 main.py
- [ ] 实现了 5 个 CRUD 端点（GET list, POST, GET detail, PATCH, DELETE）
- [ ] 所有端点使用正确的 schemas（ProjectCreate, ProjectUpdate, ProjectResponse）
- [ ] 所有端点集成了数据库会话依赖（get_db）
- [ ] 404 错误正确处理（项目不存在时）
- [ ] 集成测试覆盖所有 CRUD 操作
- [ ] Linting 检查通过
- [ ] 手动测试验证 API 功能正常

---

## COMPLETION CHECKLIST

- [ ] main.py 更新完成（CORS + router 注册）
- [ ] projects.py router 创建完成
- [ ] 5 个端点全部实现
- [ ] 集成测试创建完成
- [ ] 所有测试通过
- [ ] Linting 检查通过
- [ ] 手动 API 测试成功
- [ ] 代码审查通过

---

## NOTES

**设计决策：**

1. **最小化实现**：暂不实现 ProjectNode 端点，先完成 Project CRUD
2. **简化日志**：暂不添加 structlog 中间件，使用 FastAPI 默认日志
3. **CORS 配置**：开发环境允许 localhost:3000，生产环境需要配置环境变量
4. **错误处理**：使用 FastAPI 的 HTTPException，暂不实现自定义异常类

**实现顺序理由：**

- 先配置 FastAPI 应用（CORS）
- 再实现 router（业务逻辑）
- 最后添加测试（验证功能）

**未来考虑：**

- ProjectNode 嵌套资源端点（Plan 1.5）
- 分页支持（查询参数 limit/offset）
- 过滤和排序功能
- 认证和授权中间件
