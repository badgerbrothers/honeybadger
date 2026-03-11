# Feature: 项目基础结构搭建

## Feature Description

创建Manus MVP项目的完整目录结构、配置文件和开发环境。这是项目的第一步，为后续所有开发工作建立标准化的基础设施。

## User Story

作为开发人员
我想要有一个完整配置好的项目结构和开发环境
以便我可以立即开始实现业务逻辑而不需要手动配置基础设施

## Problem Statement

当前项目只有文档，没有实际的代码结构。需要从零开始建立：
- 三个子项目的目录结构（backend、worker、frontend）
- 各子项目的依赖配置文件
- Docker Compose服务编排
- 环境变量配置模板
- 开发工具配置

## Solution Statement

按照PRD定义的架构，创建完整的项目结构：
1. 创建所有必需的目录（遵循PRD第6节定义的结构）
2. 配置Python项目（backend和worker使用uv和pyproject.toml）
3. 配置Node.js项目（frontend使用npm和package.json）
4. 配置Docker Compose（PostgreSQL、Redis、MinIO）
5. 创建环境变量模板和开发文档

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: All (backend, worker, frontend, infrastructure)
**Dependencies**: Python 3.11+, Node.js 18+, Docker, uv, npm

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**IMPORTANT: READ THESE BEFORE IMPLEMENTING!**

- `.claude/PRD.md` (lines 207-278) - Complete directory structure definition
- `.claude/PRD.md` (lines 571-659) - Technology stack with versions
- `.claude/PRD.md` (lines 677-713) - Environment variables configuration
- `CLAUDE.md` - Project overview and commands reference
- `docs/implementation-plans.md` (lines 20-50) - Plan 1.1 detailed requirements

### New Files to Create

**Backend:**
- `backend/pyproject.toml` - Python dependencies and project metadata
- `backend/app/__init__.py` - Package marker
- `backend/app/main.py` - FastAPI entry point (placeholder)
- `backend/app/config.py` - Configuration management (placeholder)
- `backend/app/database.py` - Database connection (placeholder)

**Worker:**
- `worker/pyproject.toml` - Python dependencies for worker
- `worker/__init__.py` - Package marker

**Frontend:**
- `frontend/package.json` - Node.js dependencies
- `frontend/tsconfig.json` - TypeScript configuration
- `frontend/next.config.js` - Next.js configuration
- `frontend/.eslintrc.json` - ESLint configuration
- `frontend/tailwind.config.ts` - Tailwind CSS configuration
- `frontend/postcss.config.js` - PostCSS configuration

**Infrastructure:**
- `docker-compose.yml` - Service orchestration
- `docker/sandbox-base/Dockerfile` - Base sandbox image
- `.env.example` - Environment variables template
- `.gitignore` - Git ignore patterns (update existing)

### Relevant Documentation

**YOU SHOULD READ THESE BEFORE IMPLEMENTING!**

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
  - Why: Understanding FastAPI project structure
- [uv Documentation](https://docs.astral.sh/uv/)
  - Why: Python package management with uv
- [Next.js 14 Documentation](https://nextjs.org/docs)
  - Why: App Router and project setup
- [Docker Compose Documentation](https://docs.docker.com/compose/)
  - Why: Multi-container orchestration
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
  - Why: Database service configuration
- [Redis Docker Image](https://hub.docker.com/_/redis)
  - Why: Cache and queue service
- [MinIO Docker Image](https://hub.docker.com/r/minio/minio)
  - Why: S3-compatible object storage

### Patterns to Follow

**Directory Structure Pattern:**
```
项目根目录/
├── backend/          # Python FastAPI 后端
├── worker/           # Python 任务执行器
├── frontend/         # Next.js 前端
├── shared/           # 共享代码
└── docker/           # Docker 配置
```

**Python Project Pattern (pyproject.toml):**
- 使用 `uv` 作为包管理器
- Python 版本: 3.11+
- 使用 `tool.uv` 配置段

**Next.js Project Pattern:**
- App Router (不是 Pages Router)
- TypeScript 严格模式
- Tailwind CSS + shadcn/ui

---

## IMPLEMENTATION PLAN

### Phase 1: 创建目录结构

**Tasks:**
- 创建所有主要目录和子目录
- 创建必要的 `__init__.py` 文件（Python包标记）
- 验证目录结构完整性

### Phase 2: 配置Python项目

**Tasks:**
- 创建 backend/pyproject.toml（FastAPI相关依赖）
- 创建 worker/pyproject.toml（Docker SDK、Playwright等依赖）
- 创建占位符Python文件（main.py、config.py等）
- 使用 uv sync 验证依赖安装

### Phase 3: 配置Frontend项目

**Tasks:**
- 创建 frontend/package.json（Next.js、React、TypeScript依赖）
- 创建 TypeScript 配置文件
- 创建 Next.js 配置文件
- 创建 Tailwind CSS 配置
- 使用 npm install 验证依赖安装

### Phase 4: 配置Docker服务

**Tasks:**
- 创建 docker-compose.yml（PostgreSQL、Redis、MinIO）
- 创建基础沙箱 Dockerfile
- 创建 .env.example 环境变量模板
- 使用 docker-compose config 验证配置

### Phase 5: 更新文档和配置

**Tasks:**
- 更新 .gitignore（添加node_modules、__pycache__等）
- 更新 README.md（添加启动命令）
- 验证所有配置文件语法正确

---

## STEP-BY-STEP TASKS

### Task 1: CREATE 项目目录结构

**IMPLEMENT**: 创建完整的目录树
```bash
mkdir -p backend/app/{models,schemas,routers,services}
mkdir -p worker/{orchestrator,tools,sandbox,models,rag,memory,skills}
mkdir -p worker/rag/parsers
mkdir -p frontend/src/{app,components,features,lib,hooks}
mkdir -p frontend/src/features/{projects,conversations,tasks,artifacts}
mkdir -p shared/{schemas,utils}
mkdir -p docker/sandbox-base
```

**VALIDATE**: `find . -type d -name "backend" -o -name "worker" -o -name "frontend" | wc -l` (应返回3)

### Task 2: CREATE Python包标记文件

**IMPLEMENT**: 创建 `__init__.py` 文件使目录成为Python包
```bash
touch backend/__init__.py
touch backend/app/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/routers/__init__.py
touch backend/app/services/__init__.py
touch worker/__init__.py
touch worker/orchestrator/__init__.py
touch worker/tools/__init__.py
touch worker/sandbox/__init__.py
touch worker/models/__init__.py
touch worker/rag/__init__.py
touch worker/rag/parsers/__init__.py
touch worker/memory/__init__.py
touch worker/skills/__init__.py
touch shared/__init__.py
touch shared/schemas/__init__.py
touch shared/utils/__init__.py
```

**VALIDATE**: `find backend worker shared -name "__init__.py" | wc -l` (应返回18)

### Task 3: CREATE backend/pyproject.toml

**IMPLEMENT**: Backend Python项目配置文件

**PATTERN**: 使用uv包管理器，Python 3.11+

**CONTENT**:
```toml
[project]
name = "manus-backend"
version = "0.1.0"
description = "Manus MVP Backend API"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "structlog>=24.1.0",
    "httpx>=0.26.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
]
```

**VALIDATE**: `cd backend && uv sync` (应成功安装依赖)

### Task 4: CREATE worker/pyproject.toml

**IMPLEMENT**: Worker Python项目配置文件

**CONTENT**:
```toml
[project]
name = "manus-worker"
version = "0.1.0"
description = "Manus MVP Task Execution Worker"
requires-python = ">=3.11"
dependencies = [
    "docker>=7.0.0",
    "playwright>=1.40.0",
    "openai>=1.10.0",
    "anthropic>=0.18.0",
    "redis>=5.0.0",
    "celery>=5.3.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.9",
    "pydantic>=2.0.0",
    "structlog>=24.1.0",
    "httpx>=0.26.0",
    "beautifulsoup4>=4.12.0",
    "pypdf>=4.0.0",
    "python-multipart>=0.0.6",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
]
```

**VALIDATE**: `cd worker && uv sync` (应成功安装依赖)

### Task 5: CREATE frontend/package.json

**IMPLEMENT**: Frontend Node.js项目配置文件

**CONTENT**:
```json
{
  "name": "manus-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.17.0",
    "zustand": "^4.5.0",
    "zod": "^3.22.0",
    "date-fns": "^3.3.0",
    "lucide-react": "^0.323.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/node": "^20.11.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.56.0",
    "eslint-config-next": "^14.1.0"
  }
}
```

**VALIDATE**: `cd frontend && npm install` (应成功安装依赖)

### Task 6: CREATE frontend/tsconfig.json

**IMPLEMENT**: TypeScript配置文件

**CONTENT**:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**VALIDATE**: `cd frontend && npx tsc --noEmit` (应无类型错误)

### Task 7: CREATE frontend/next.config.js

**IMPLEMENT**: Next.js配置文件

**CONTENT**:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = nextConfig
```

**VALIDATE**: 文件存在且语法正确

### Task 8: CREATE frontend/tailwind.config.ts

**IMPLEMENT**: Tailwind CSS配置文件

**CONTENT**:
```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
export default config
```

**VALIDATE**: 文件存在且语法正确

### Task 9: CREATE frontend/postcss.config.js

**IMPLEMENT**: PostCSS配置文件

**CONTENT**:
```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**VALIDATE**: 文件存在且语法正确


### Task 10: CREATE docker-compose.yml

**IMPLEMENT**: Docker服务编排配置

**CONTENT**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: manus
      POSTGRES_PASSWORD: manus_dev_password
      POSTGRES_DB: manus
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: manus
      MINIO_ROOT_PASSWORD: manus_dev_password
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

**VALIDATE**: `docker-compose config` (应无语法错误)


### Task 11: CREATE .env.example

**IMPLEMENT**: 环境变量模板文件

**CONTENT**:
```bash
# Database
DATABASE_URL=postgresql://manus:manus_dev_password@localhost:5432/manus
POSTGRES_USER=manus
POSTGRES_PASSWORD=manus_dev_password
POSTGRES_DB=manus

# Redis
REDIS_URL=redis://localhost:6379/0

# Object Storage (MinIO)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=manus
S3_SECRET_KEY=manus_dev_password
S3_BUCKET=manus-artifacts

# Model Providers
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Default Models
DEFAULT_MAIN_MODEL=gpt-4-turbo-preview
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small

# Sandbox
DOCKER_HOST=unix:///var/run/docker.sock
SANDBOX_TIMEOUT=300
SANDBOX_MEMORY_LIMIT=2g
SANDBOX_CPU_LIMIT=2.0

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

**VALIDATE**: 文件存在且格式正确


### Task 12: UPDATE .gitignore

**IMPLEMENT**: 添加缺失的忽略规则（现有文件已包含部分规则）

**ADD** 到.gitignore末尾:
```
# Python (additional)
*.py[cod]
*$py.class
*.so
.uv/
*.egg-info/
dist/
build/

# Node.js (additional)
.next/
out/
*.log
npm-debug.log*

# Environment (additional)
.env.local

# IDE (additional)
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
*.pid
```

**VALIDATE**: `git check-ignore .next` (应返回.next)


### Task 13: CREATE backend占位符文件

**IMPLEMENT**: 创建基础Python文件以验证结构

**CREATE** `backend/app/main.py`:
```python
"""FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(title="Manus MVP Backend")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

**CREATE** `backend/app/config.py`:
```python
"""Configuration management."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://manus:manus_dev_password@localhost:5432/manus"
    redis_url: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**CREATE** `backend/app/database.py`:
```python
"""Database connection setup."""
# Placeholder for SQLAlchemy setup
```

**VALIDATE**: `cd backend && python -c "from app.main import app; print('OK')"` (应输出OK)


### Task 14: CREATE docker/sandbox-base/Dockerfile

**IMPLEMENT**: 基础沙箱镜像

**CONTENT**:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    requests \
    beautifulsoup4

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

CMD ["/bin/bash"]
```

**VALIDATE**: `docker build -t manus-sandbox-base docker/sandbox-base/` (应成功构建)


### Task 15: VERIFY README.md

**IMPLEMENT**: 验证README.md已包含必要内容

**CHECK**: README.md应包含以下部分：
- ✓ Quick Start指南
- ✓ 架构图
- ✓ 技术栈
- ✓ 启动命令（docker-compose和手动）
- ✓ API端点列表
- ✓ 配置说明

**NOTE**: README.md已经完整，无需修改

**VALIDATE**: `grep "Quick Start" README.md` (应找到内容)

---

## TESTING STRATEGY

### 结构验证

- 验证所有目录已创建
- 验证所有__init__.py文件存在
- 验证配置文件语法正确

### 依赖安装测试

- Backend: `cd backend && uv sync`
- Worker: `cd worker && uv sync`
- Frontend: `cd frontend && npm install`

### Docker服务测试

- 验证docker-compose配置: `docker-compose config`
- 启动服务: `docker-compose up -d`
- 检查服务状态: `docker-compose ps`


---

## VALIDATION COMMANDS

### Level 1: 目录结构验证

```bash
# 验证主要目录存在
test -d backend && test -d worker && test -d frontend && echo "✓ 主要目录存在"

# 验证Python包标记
find backend worker shared -name "__init__.py" | wc -l
# 预期: 18

# 验证配置文件存在
test -f backend/pyproject.toml && test -f worker/pyproject.toml && test -f frontend/package.json && echo "✓ 配置文件存在"
```

### Level 2: 配置文件语法验证

```bash
# 验证docker-compose配置
docker-compose config

# 验证Python项目配置
cd backend && uv sync --dry-run
cd worker && uv sync --dry-run

# 验证TypeScript配置
cd frontend && npx tsc --noEmit
```


### Level 3: 依赖安装验证

```bash
# 安装Backend依赖
cd backend && uv sync
echo "✓ Backend依赖安装完成"

# 安装Worker依赖
cd worker && uv sync
echo "✓ Worker依赖安装完成"

# 安装Frontend依赖
cd frontend && npm install
echo "✓ Frontend依赖安装完成"
```

### Level 4: Docker服务验证

```bash
# 启动所有服务
docker-compose up -d

# 等待服务启动
sleep 5

# 检查服务状态
docker-compose ps

# 验证PostgreSQL
docker-compose exec postgres pg_isready -U manus

# 验证Redis
docker-compose exec redis redis-cli ping

# 验证MinIO
curl -I http://localhost:9000/minio/health/live
```


---

## ACCEPTANCE CRITERIA

- [ ] 所有目录按PRD定义的结构创建完成
- [ ] backend/pyproject.toml包含所有必需依赖
- [ ] worker/pyproject.toml包含所有必需依赖
- [ ] frontend/package.json包含所有必需依赖
- [ ] docker-compose.yml配置正确且可启动
- [ ] .env.example包含所有环境变量
- [ ] .gitignore包含Python和Node.js忽略规则
- [ ] `uv sync`在backend和worker中成功执行
- [ ] `npm install`在frontend中成功执行
- [ ] `docker-compose up -d`成功启动所有服务
- [ ] PostgreSQL、Redis、MinIO服务健康检查通过
- [ ] README.md包含完整的启动命令


---

## COMPLETION CHECKLIST

- [ ] Task 1-15全部完成
- [ ] 所有验证命令执行成功
- [ ] Docker服务全部启动并运行正常
- [ ] Backend可以通过uv运行
- [ ] Frontend可以通过npm运行
- [ ] 无配置文件语法错误
- [ ] 目录结构与PRD定义一致

---

## NOTES

### 设计决策

1. **使用uv而非pip**: uv是更快的Python包管理器，符合现代Python项目最佳实践
2. **Next.js App Router**: 使用最新的App Router而非Pages Router
3. **Docker Compose版本3.8**: 兼容性好且功能完整
4. **开发环境密码**: 使用简单密码便于本地开发，生产环境需更改

### 关键依赖说明

- **FastAPI 0.110+**: 需要此版本以支持最新的async特性
- **SQLAlchemy 2.0+**: 使用新的async API
- **Next.js 14+**: 需要App Router支持
- **PostgreSQL 15+**: 需要pgvector扩展支持

### 后续步骤

完成此Plan后，继续执行：
- Plan 1.2: 数据库模式和模型
- Plan 1.3: Pydantic Schemas

