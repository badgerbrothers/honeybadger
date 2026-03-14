# Badgers MVP

An AI-powered task execution platform where users delegate complex, multi-step workflows to an autonomous agent. The agent executes tasks in isolated Docker sandboxes using real tools (browser, code, files), producing persistent artifacts that save to project directories.

## Prerequisites

- **Python 3.11+** with [uv](https://github.com/astral-sh/uv) package manager
- **Node.js 18+** with npm
- **Docker** and Docker Compose
- **PostgreSQL 15+** (or use Docker Compose)
- **Redis 7+** (or use Docker Compose)

## Quick Start

### Option 1: Docker Compose (Infrastructure Only)

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=your-key
# ANTHROPIC_API_KEY=your-key

# Start infrastructure services
docker-compose up -d

# View infrastructure logs
docker-compose logs -f
```

This compose file currently starts only the development dependencies:
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MinIO API: `localhost:9000`
- MinIO Console: `localhost:9001`

Start `backend`, `worker`, and `frontend` separately with the manual setup below.

### Option 2: Manual Setup

#### 1. Setup Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

#### 2. Setup Worker (new terminal)

```bash
cd worker
uv sync
uv run python -m worker.main
```

#### 3. Setup Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Navigate to **http://localhost:3000** to start using Badgers.

## Architecture

```
┌─────────────┐
│   Frontend  │ (Next.js)
│   Port 3000 │
└──────┬──────┘
       │ HTTP/WebSocket
┌──────▼──────────────────────────────────────┐
│         FastAPI Backend (Control Plane)      │
│  - Project API                               │
│  - Conversation API                          │
│  - Task API                                  │
│  - Artifact API                              │
└──────┬──────────────────────────────────────┘
       │ DB Polling (current scheduler baseline)
┌──────▼──────────────────────────────────────┐
│      Python Worker (Execution Plane)         │
│  - Agent Orchestrator                        │
│  - Tool System                               │
│  - Sandbox Manager                           │
└──────┬──────────────────────────────────────┘
       │
┌──────▼──────┐  ┌──────────┐  ┌──────────┐
│   Docker    │  │ Postgres │  │  MinIO   │
│  Sandboxes  │  │ +pgvector│  │ (S3-like)│
└─────────────┘  └──────────┘  └──────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, structlog |
| Worker | Python worker loop, Docker SDK, Playwright |
| Frontend | Next.js 14, React 18, TypeScript, TanStack Query, Tailwind CSS |
| AI/ML | OpenAI SDK, Anthropic SDK, pgvector |
| Storage | MinIO (S3-compatible), PostgreSQL |
| Queue | PostgreSQL polling today, Redis reserved for future queueing |

## Features

### Core Capabilities

- **Project Management** — Create workspaces to organize tasks and files
- **Task Execution** — Delegate complex multi-step workflows to AI agent
- **Isolated Sandboxes** — Each task runs in its own Docker container
- **Real-time Updates** — See agent progress with live step-by-step updates
- **Tool System** — Agent uses browser, code execution, file operations, web APIs
- **Artifact Generation** — Tasks produce persistent outputs (reports, code, screenshots)
- **RAG Integration** — Agent retrieves context from project files
- **Memory System** — Conversation summaries and project facts persist across tasks
- **Multi-Model Support** — Works with OpenAI, Anthropic, and compatible APIs

### Example Use Cases

1. **Research Reports** — "Research Tesla Q4 earnings and create a markdown report"
2. **Web Development** — "Create a landing page with pricing tiers"
3. **Data Analysis** — "Analyze this CSV and generate visualizations"
4. **Document Processing** — "Extract key terms from these PDFs"

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects/` | Create new project |
| GET | `/api/projects/{id}` | Get project details |
| POST | `/api/conversations/` | Create conversation |
| POST | `/api/conversations/{id}/messages` | Create conversation message |
| POST | `/api/tasks/` | Create task manually |
| POST | `/api/tasks/{id}/runs` | Create a new task run |
| POST | `/api/tasks/{id}/retry` | Retry an existing task |
| GET | `/api/runs/{id}` | Get run details |
| WS | `/api/runs/{id}/stream` | Stream run events |
| GET | `/api/artifacts/{id}/download` | Download artifact |

Full API documentation available at http://localhost:8000/docs when backend is running.

## Configuration

Key environment variables (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/badgers

# Redis
REDIS_URL=redis://localhost:6379/0

# Object Storage
S3_ENDPOINT=localhost:9000
S3_BUCKET=badgers-artifacts
S3_SECURE=false

# Model Providers
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
DEFAULT_MAIN_MODEL=gpt-4-turbo-preview

# Sandbox
SANDBOX_TIMEOUT=300
SANDBOX_MEMORY_LIMIT=2g
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
uv run pytest tests/ -v
uv run pytest --cov=app

# Frontend tests
cd frontend
npm run test
npx playwright test
```

### Project Structure

```
badgers-mvp/
├── backend/          # FastAPI application
├── worker/           # Task execution worker
├── frontend/         # Next.js application
├── shared/           # Shared utilities
├── docker/           # Docker configurations
├── docs/             # Documentation
└── .claude/          # PRD and reference docs
```

## Claude Commands

Slash commands for Claude Code to assist with development workflows:

### Planning & Execution
| Command | Description |
|---------|-------------|
| `/core_piv_loop:prime` | Load project context and codebase understanding |
| `/core_piv_loop:plan-feature` | Create comprehensive implementation plan |
| `/core_piv_loop:execute` | Execute an implementation plan step-by-step |

### Validation
| Command | Description |
|---------|-------------|
| `/validation:validate` | Run full validation: tests, linting, coverage |
| `/validation:code-review` | Technical code review on changed files |
| `/validation:code-review-fix` | Fix issues found in code review |

### Misc
| Command | Description |
|---------|-------------|
| `/commit` | Create atomic commit with appropriate tag |
| `/create-prd` | Generate Product Requirements Document |

## Documentation

- **PRD**: `.claude/PRD.md` - Complete product requirements and architecture
- **Requirements**: `docs/badgers-mvp-requirements.md` - Original detailed requirements (Chinese)
- **API Docs**: http://localhost:8000/docs - Interactive API documentation

## License

MIT
