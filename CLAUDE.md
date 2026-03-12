# Badgers MVP

An AI-powered task execution platform that enables users to delegate complex, multi-step workflows to an autonomous agent with isolated execution environments.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, structlog
- **Frontend**: Next.js 14+, React 18, TypeScript, Tailwind CSS, TanStack Query
- **Task Queue**: Redis, ARQ/Celery
- **Sandbox**: Docker, Playwright
- **Storage**: MinIO (S3-compatible), pgvector
- **AI/ML**: OpenAI SDK, Anthropic SDK

## Project Structure

```
badgers-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Configuration management
│   │   ├── database.py       # PostgreSQL connection
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── routers/          # API endpoints
│   │   │   ├── projects.py
│   │   │   ├── conversations.py
│   │   │   ├── tasks.py
│   │   │   └── artifacts.py
│   │   └── services/         # Business logic
│   └── pyproject.toml
├── worker/
│   ├── orchestrator/         # Agent orchestration
│   ├── tools/                # Tool implementations
│   ├── sandbox/              # Sandbox management
│   ├── models/               # Model abstraction
│   ├── rag/                  # RAG system
│   ├── memory/               # Memory system
│   └── skills/               # Skill templates
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   ├── components/       # React components
│   │   ├── features/         # Feature modules
│   │   │   ├── projects/
│   │   │   ├── conversations/
│   │   │   ├── tasks/
│   │   │   └── artifacts/
│   │   └── lib/              # Utilities, API client
│   └── package.json
├── shared/                   # Shared utilities
└── docker/                   # Docker configurations
```

## Commands

```bash
# Backend
cd backend && uv sync
uv run uvicorn app.main:app --reload --port 8000

# Worker
cd worker && uv sync
uv run python -m worker.main

# Frontend
cd frontend && npm install && npm run dev

# Full Stack (Docker Compose)
docker-compose up -d

# Testing
cd backend && uv run pytest tests/ -v
cd frontend && npm run test
npx playwright test
```

## Reference Documentation

Read these documents when working on specific areas:

| Document | When to Read |
|----------|--------------|
| `.claude/PRD.md` | Understanding requirements, features, architecture, API spec |
| `docs/badgers-mvp-requirements.md` | Original detailed requirements (Chinese) |

## Core Concepts

### Architecture Flow
```
Conversation → Task → Run → Sandbox → Artifact → Project
```

- **Project**: Long-term workspace containing files and task outputs
- **Conversation**: Chat interface for task initiation
- **Task**: Goal-oriented unit of work (e.g., "research Tesla earnings")
- **Run**: Single execution instance with isolated sandbox
- **Sandbox**: Docker container where agent executes tools
- **Artifact**: Generated output (report, code, screenshot)

### Tool System

Agent has access to these tools:
- `browser.*` - Open, click, type, extract, screenshot
- `file.*` - List, read, write files
- `python.run` - Execute Python code
- `web.fetch` - HTTP requests
- `final.answer` - Submit task result

### Skills

Lightweight task templates defined in Markdown files (`worker/skills/*/SKILL.md`):
- **research_report** - Web research and markdown report generation
- **webpage** - HTML/CSS/JS code generation
- **file_analysis** - Document analysis and insights

Each skill defines:
- System prompt to guide agent behavior
- Allowed tools the agent can use
- Output format specification
- Example tasks

