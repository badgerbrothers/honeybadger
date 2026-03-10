# Manus MVP - Product Requirements Document

## 1. Executive Summary

Manus MVP is an AI-powered task execution platform that enables users to delegate complex, multi-step workflows to an autonomous agent. Unlike traditional chatbots, Manus creates isolated execution environments (sandboxes) for each task, allowing the agent to use real tools—browsers, code interpreters, file systems—to accomplish goals like generating research reports, building web pages, or analyzing documents.

The core innovation is the task execution loop: users initiate tasks through conversations, the system creates a dedicated sandbox, the agent executes multiple steps using available tools, and results are captured as artifacts that persist in project directories. This transforms AI from a conversational assistant into an autonomous worker capable of producing tangible deliverables.

The MVP validates whether a single-agent execution model can reliably complete real-world tasks end-to-end, establishing the foundation for future multi-agent collaboration and enterprise features.

## 2. Mission

**Mission Statement:** Empower users to delegate complex, multi-step tasks to AI agents that can autonomously execute workflows using real tools, producing tangible artifacts that persist beyond conversations.

**Core Principles:**

1. **Task-Centric, Not Chat-Centric:** Conversations are interfaces for task initiation; the core product is reliable task execution with observable progress and persistent results.

2. **Isolation by Default:** Each task run operates in its own sandbox with independent state, preventing interference and enabling safe experimentation.

3. **Artifacts Over Ephemeral Responses:** Task outputs are structured artifacts (reports, code, data files) that save to project directories, not just chat messages that scroll away.

4. **Observable Execution:** Users see step-by-step progress, tool calls, and intermediate results, building trust through transparency.

5. **Model-Agnostic Architecture:** The system abstracts model providers, supporting OpenAI-compatible APIs, Anthropic, and future local/self-hosted models without coupling business logic to specific SDKs.

## 3. Target Users

### Primary Persona: Technical Professionals

**Profile:**
- Software developers, data analysts, researchers, product managers
- Comfortable with technical concepts but want to offload repetitive or time-consuming tasks
- Work on projects requiring research, code generation, data analysis, or content creation
- Value automation but need visibility into what the AI is doing

**Technical Comfort Level:**
- Understand file systems, APIs, basic programming concepts
- Comfortable with markdown, JSON, command-line tools
- May not be AI/ML experts but understand LLM capabilities and limitations

**Key Needs:**
- Delegate multi-step workflows without writing custom scripts
- See what the AI is doing at each step (transparency)
- Get structured outputs (files, reports, code) not just text responses
- Organize work in projects with persistent file storage
- Retry failed tasks without losing context

**Pain Points:**
- Current AI chat tools don't produce persistent, structured outputs
- No way to give AI access to real tools (browsers, code execution)
- Difficult to track what AI did across multiple steps
- Results disappear when conversation ends
- Can't build on previous work in a structured way

## 4. MVP Scope

### ✅ In Scope

**Core Functionality:**
- ✅ Create and manage projects with directory structures
- ✅ Initiate tasks through conversation interface
- ✅ Single-agent multi-step task execution loop
- ✅ Independent sandbox per task run (Docker-based)
- ✅ Real-time task status updates (pending, running, success, failed, cancelled)
- ✅ Task retry capability with new run instances
- ✅ Artifact generation and export to project directories
- ✅ View task execution logs and tool call history

**Tool System:**
- ✅ Browser automation (open, click, type, extract, screenshot)
- ✅ File operations (list, read, write)
- ✅ Python code execution
- ✅ Web content fetching
- ✅ Final answer/result submission

**Data & Context:**
- ✅ Lightweight RAG for project files (PDF, Markdown, TXT, web content)
- ✅ Project-scoped document retrieval
- ✅ Three-tier memory: conversation summaries, project facts, task working memory
- ✅ File upload to projects

**Technical:**
- ✅ Unified model abstraction layer (OpenAI-compatible + Anthropic native)
- ✅ Basic model routing (default main model, default embedding model, per-task override)
- ✅ WebSocket or SSE for real-time task events
- ✅ Structured logging for observability

**Skills:**
- ✅ Lightweight skill templates (research reports, web page generation, file analysis)
- ✅ Skill-specific system prompts and tool restrictions

### ❌ Out of Scope (Future Phases)

**Collaboration:**
- ❌ Multi-agent parallel execution
- ❌ Team collaboration features
- ❌ Organization/permission management
- ❌ Real-time multi-user editing

**Platform:**
- ❌ Plugin marketplace
- ❌ Full MCP ecosystem integration
- ❌ Mobile/desktop native clients
- ❌ Website hosting/deployment platform
- ❌ Complex approval workflows

**Advanced Features:**
- ❌ Multi-thread conversations
- ❌ Complex long-term memory networks
- ❌ Advanced model routing (auto-fallback, cost optimization)
- ❌ Visual model capabilities (image generation, vision)

## 5. User Stories

### Primary User Stories

**US-1: Research Report Generation**
- **As a** researcher
- **I want to** ask the system to investigate a topic and generate a comprehensive report
- **So that** I can save hours of manual research and get structured, cited findings
- **Example:** "Research Tesla's Q4 2025 earnings and create a summary report with key metrics"

**US-2: Web Page Creation**
- **As a** developer
- **I want to** request a landing page or web component
- **So that** I can quickly prototype ideas without writing boilerplate HTML/CSS/JS
- **Example:** "Create a pricing page with three tiers and a comparison table"

**US-3: Document Analysis**
- **As a** analyst
- **I want to** upload PDFs or documents and ask questions about their content
- **So that** I can extract insights without manually reading hundreds of pages
- **Example:** "Analyze this contract PDF and list all payment terms and deadlines"

**US-4: Task Progress Monitoring**
- **As a** user
- **I want to** see real-time updates as the agent executes each step
- **So that** I understand what's happening and can intervene if needed
- **Example:** See "Opening browser → Searching for data → Extracting table → Generating report"

**US-5: Task Retry After Failure**
- **As a** user
- **I want to** retry a failed task without re-explaining the goal
- **So that** I can recover from transient errors or timeout issues
- **Example:** Task fails due to network timeout; click "Retry" to create new run

**US-6: Project Organization**
- **As a** user
- **I want to** organize all task outputs in a project directory structure
- **So that** I can find and reuse artifacts from previous tasks
- **Example:** All research reports save to `/reports/`, web pages to `/sites/`

**US-7: Context-Aware Follow-Up Tasks**
- **As a** user
- **I want to** initiate new tasks that build on previous project files
- **So that** I can iteratively develop complex deliverables
- **Example:** "Add a contact form to the landing page you created earlier"

**US-8: Multi-Step Automation**
- **As a** user
- **I want to** delegate tasks requiring multiple tools (browser + code + files)
- **So that** I can automate workflows that would take me hours manually
- **Example:** "Scrape competitor pricing, analyze with Python, generate comparison chart"

## 6. Core Architecture & Patterns

### High-Level Architecture

**Modular Monolith Approach:**
- Single codebase with clear module boundaries
- Control plane (API) separated from execution plane (workers)
- Async task execution with queue-based orchestration
- Stateless API layer, stateful worker processes

**Key Components:**

```
┌─────────────┐
│   Frontend  │ (Next.js)
│   (Web UI)  │
└──────┬──────┘
       │ HTTP/WebSocket
┌──────▼──────────────────────────────────────┐
│         FastAPI Backend (Control Plane)      │
│  - Project API                               │
│  - Conversation API                          │
│  - Task API                                  │
│  - Artifact API                              │
│  - WebSocket/SSE event streaming             │
└──────┬──────────────────────────────────────┘
       │ Redis Queue
┌──────▼──────────────────────────────────────┐
│      Python Worker (Execution Plane)         │
│  - Agent Orchestrator                        │
│  - Tool System                               │
│  - Sandbox Manager                           │
│  - Model Router                              │
└──────┬──────────────────────────────────────┘
       │
┌──────▼──────┐  ┌──────────┐  ┌──────────┐
│   Docker    │  │ Postgres │  │  MinIO   │
│  Sandboxes  │  │ +pgvector│  │ (S3-like)│
└─────────────┘  └──────────┘  └──────────┘
```

### Directory Structure

```
manus-mvp/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # Reusable UI components
│   │   ├── features/        # Feature modules
│   │   │   ├── projects/
│   │   │   ├── conversations/
│   │   │   ├── tasks/
│   │   │   └── artifacts/
│   │   ├── lib/             # Utilities, API client
│   │   └── hooks/           # Custom React hooks
│   └── package.json
│
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database connection
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── routers/         # API endpoints
│   │   │   ├── projects.py
│   │   │   ├── conversations.py
│   │   │   ├── tasks.py
│   │   │   └── artifacts.py
│   │   ├── services/        # Business logic
│   │   └── dependencies.py  # FastAPI dependencies
│   └── pyproject.toml
│
├── worker/                   # Task execution worker
│   ├── orchestrator/        # Agent orchestration
│   │   ├── agent.py         # Main agent loop
│   │   ├── planner.py       # Task planning
│   │   └── executor.py      # Step execution
│   ├── tools/               # Tool implementations
│   │   ├── base.py          # Tool interface
│   │   ├── browser.py       # Browser automation
│   │   ├── file.py          # File operations
│   │   ├── python.py        # Code execution
│   │   └── web.py           # Web fetching
│   ├── sandbox/             # Sandbox management
│   │   ├── manager.py       # Lifecycle management
│   │   └── docker_backend.py
│   ├── models/              # Model abstraction
│   │   ├── base.py          # Unified interface
│   │   ├── openai_compat.py
│   │   └── anthropic.py
│   ├── rag/                 # RAG system
│   │   ├── indexer.py       # Document indexing
│   │   ├── retriever.py     # Similarity search
│   │   └── parsers/         # Document parsers
│   ├── memory/              # Memory system
│   │   ├── conversation.py
│   │   ├── project.py
│   │   └── working.py
│   └── skills/              # Skill templates
│       ├── research.py
│       ├── webpage.py
│       └── analysis.py
│
├── shared/                   # Shared utilities
│   ├── schemas/             # Shared data models
│   └── utils/
│
└── docker/                   # Docker configurations
    ├── sandbox-base/        # Base sandbox image
    └── docker-compose.yml
```

### Key Design Patterns

**1. Task-Run Separation:**
- `Task` = logical goal (e.g., "research Tesla earnings")
- `Run` = execution instance with its own sandbox and logs
- Enables retry without duplicating task definition

**2. Tool Interface Pattern:**
```python
class Tool(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    async def execute(self, params: dict) -> ToolResult:
        pass
```

**3. Sandbox Lifecycle:**
- Create → Mount working directory → Execute tools → Capture artifacts → Destroy
- Each run gets isolated filesystem and network namespace

**4. Event Streaming:**
- Workers emit events (step_started, tool_called, artifact_created)
- API streams events to frontend via WebSocket/SSE
- Frontend updates UI in real-time

**5. Artifact Flow:**
```
Sandbox temp files → Artifact (S3/MinIO) → Project directory (user-initiated save)
```

## 7. Tools/Features

### Tool System Design

Each tool follows a unified interface with consistent parameter structure and return format. All tool executions are logged and results are displayable in the frontend.

#### Browser Tools

**Purpose:** Enable web automation, data extraction, and screenshot capture.

**Operations:**

1. **browser.open**
   - Opens URL in headless browser
   - Returns: page title, URL, success status
   - Example: `{"url": "https://example.com", "wait_for": "networkidle"}`

2. **browser.click**
   - Clicks element by selector
   - Returns: success status, element text
   - Example: `{"selector": "button.submit", "wait_for_navigation": true}`

3. **browser.type**
   - Types text into input field
   - Returns: success status
   - Example: `{"selector": "input[name='search']", "text": "Tesla earnings"}`

4. **browser.extract**
   - Extracts structured data from page
   - Returns: extracted content (text, tables, links)
   - Example: `{"selector": "table.data", "format": "json"}`

5. **browser.screenshot**
   - Captures page screenshot
   - Returns: image artifact reference
   - Example: `{"full_page": true, "format": "png"}`

**Key Features:**
- Playwright-based automation
- Automatic wait for page load
- Element visibility checks
- Screenshot artifacts saved to S3

#### File Tools

**Purpose:** Read, write, and manage files in sandbox and project directories.

**Operations:**

1. **file.list**
   - Lists files in directory
   - Returns: file paths, sizes, modified times
   - Example: `{"path": "/workspace", "recursive": true}`

2. **file.read**
   - Reads file content
   - Returns: file content (text or base64 for binary)
   - Example: `{"path": "/workspace/data.json"}`

3. **file.write**
   - Writes content to file
   - Returns: success status, file path
   - Example: `{"path": "/workspace/report.md", "content": "# Report..."}`

**Key Features:**
- Sandbox filesystem isolation
- Support for text and binary files
- Automatic directory creation
- File size limits for safety

#### Python Execution Tool

**Purpose:** Execute Python code for data processing, analysis, and computation.

**Operations:**

1. **python.run**
   - Executes Python code in sandbox
   - Returns: stdout, stderr, execution time
   - Example: `{"code": "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.describe())"}`

**Key Features:**
- Isolated Python environment
- Pre-installed common libraries (pandas, numpy, requests, beautifulsoup4)
- Timeout protection (30s default)
- Stdout/stderr capture

#### Web Fetch Tool

**Purpose:** Fetch web content without full browser automation.

**Operations:**

1. **web.fetch**
   - Fetches URL content via HTTP
   - Returns: HTML/JSON content, status code, headers
   - Example: `{"url": "https://api.example.com/data", "method": "GET"}`

**Key Features:**
- Fast alternative to browser for simple requests
- Support for GET/POST methods
- Custom headers and authentication
- JSON response parsing

#### Final Answer Tool

**Purpose:** Signal task completion and submit final result.

**Operations:**

1. **final.answer**
   - Submits final task result
   - Returns: task completion status
   - Example: `{"answer": "Research complete. Report saved to /reports/tesla-q4.md", "artifacts": ["report-123", "chart-456"]}`

**Key Features:**
- Marks task as complete
- Links artifacts to task result
- Provides user-facing summary

### Skill System

Skills are lightweight task templates that configure the agent's behavior for specific task types.

**Skill Structure:**
```python
class Skill:
    name: str
    description: str
    system_prompt: str
    allowed_tools: List[str]
    output_format: str
    example_tasks: List[str]
```

**Built-in Skills:**

1. **Research Report Skill**
   - System prompt: "You are a research assistant. Search for information, extract key facts, and generate a structured markdown report with citations."
   - Allowed tools: browser.*, web.fetch, file.write, final.answer
   - Output format: Markdown report with sections (Executive Summary, Findings, Sources)

2. **Web Page Generation Skill**
   - System prompt: "You are a web developer. Generate clean, responsive HTML/CSS/JS code following modern best practices."
   - Allowed tools: file.write, python.run (for templating), final.answer
   - Output format: HTML file with embedded CSS/JS or separate files

3. **File Analysis Skill**
   - System prompt: "You are a data analyst. Read files, extract insights, and generate summary reports."
   - Allowed tools: file.read, python.run, file.write, final.answer
   - Output format: Analysis report with key findings and visualizations

## 8. Technology Stack

### Backend

**Core Framework:**
- **FastAPI 0.110+** - Modern async web framework with automatic OpenAPI docs
- **Python 3.11+** - Type hints, performance improvements

**Database:**
- **PostgreSQL 15+** - Primary relational database
- **pgvector** - Vector similarity search for RAG
- **SQLAlchemy 2.0+** - ORM with async support
- **Alembic** - Database migrations

**Task Queue:**
- **Redis 7+** - Message broker and cache
- **Celery** or **ARQ** - Async task queue (ARQ preferred for simpler async/await)

**Object Storage:**
- **MinIO** - S3-compatible object storage for artifacts
- **boto3** - S3 client library

**Sandbox:**
- **Docker Engine** - Container runtime
- **docker-py** - Python Docker SDK

**Browser Automation:**
- **Playwright** - Headless browser automation

**AI/ML:**
- **OpenAI Python SDK** - OpenAI-compatible API client
- **Anthropic Python SDK** - Claude API client
- **sentence-transformers** - Embedding generation (optional, for local embeddings)

**Utilities:**
- **Pydantic 2.0+** - Data validation and serialization
- **structlog** - Structured logging
- **httpx** - Async HTTP client
- **python-multipart** - File upload support
- **python-jose** - JWT handling (future auth)

### Frontend

**Core Framework:**
- **Next.js 14+** - React framework with App Router
- **React 18+** - UI library
- **TypeScript 5+** - Type safety

**State Management:**
- **TanStack Query (React Query) 5+** - Server state management
- **Zustand** - Client state management (lightweight)

**UI Components:**
- **Tailwind CSS 3+** - Utility-first CSS
- **shadcn/ui** - Accessible component library
- **Radix UI** - Headless UI primitives
- **Lucide React** - Icon library

**Real-time:**
- **Socket.IO Client** or **native WebSocket** - Real-time task updates

**Utilities:**
- **Zod** - Schema validation
- **date-fns** - Date manipulation
- **react-hook-form** - Form handling

### Infrastructure

**Containerization:**
- **Docker** - Application containers
- **Docker Compose** - Local development orchestration

**Reverse Proxy:**
- **Nginx** - API gateway and static file serving

**Monitoring (Optional for MVP):**
- **Prometheus** - Metrics collection
- **Grafana** - Metrics visualization

### Development Tools

- **uv** - Fast Python package manager
- **pytest** - Python testing
- **Vitest** - Frontend unit testing
- **Playwright** - E2E testing
- **ESLint** - JavaScript linting
- **Prettier** - Code formatting
- **Ruff** - Python linting and formatting

## 9. Security & Configuration

### Authentication & Authorization

**MVP Approach:**
- **No authentication** - Single-user local deployment
- **Future:** JWT-based authentication with user accounts

**Sandbox Security:**
- Each task run executes in isolated Docker container
- Network access controlled via Docker networking
- Filesystem isolation with mounted volumes
- Resource limits (CPU, memory, disk)
- Automatic cleanup after task completion

### Configuration Management

**Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/manus
POSTGRES_USER=manus
POSTGRES_PASSWORD=<secure-password>

# Redis
REDIS_URL=redis://localhost:6379/0

# Object Storage
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=<access-key>
S3_SECRET_KEY=<secret-key>
S3_BUCKET=manus-artifacts

# Model Providers
OPENAI_API_KEY=<key>
OPENAI_BASE_URL=https://api.openai.com/v1  # or compatible endpoint
ANTHROPIC_API_KEY=<key>

# Default Models
DEFAULT_MAIN_MODEL=gpt-4-turbo-preview
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small

# Sandbox
DOCKER_HOST=unix:///var/run/docker.sock
SANDBOX_TIMEOUT=300  # seconds
SANDBOX_MEMORY_LIMIT=2g
SANDBOX_CPU_LIMIT=2.0

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

**Configuration Files:**
- `backend/config.py` - Pydantic Settings for type-safe config
- `.env.example` - Template for environment variables
- `docker-compose.yml` - Service orchestration

### Security Scope

**✅ In Scope:**
- Sandbox isolation per task run
- Resource limits on sandboxes
- Network access control
- Secure credential storage (environment variables)
- Input validation on all API endpoints
- SQL injection prevention (SQLAlchemy ORM)

**❌ Out of Scope (MVP):**
- User authentication and authorization
- API rate limiting
- Audit logging
- Encryption at rest
- RBAC (Role-Based Access Control)
- OAuth/SSO integration

### Deployment Considerations

**MVP Deployment:**
- Docker Compose for local/single-server deployment
- All services on single host
- SQLite or PostgreSQL for database
- Local filesystem or MinIO for object storage

**Production Readiness (Future):**
- Kubernetes orchestration
- Managed database (RDS, Cloud SQL)
- Managed object storage (S3, GCS)
- Load balancing
- Auto-scaling workers
- Distributed tracing

## 10. API Specification

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
MVP: No authentication required. Future: Bearer token in Authorization header.

### Core Endpoints

#### Projects

**POST /projects**
- Create new project
- Request:
```json
{
  "name": "My Research Project",
  "description": "Q4 2025 market analysis"
}
```
- Response: 201 Created
```json
{
  "id": "proj_abc123",
  "name": "My Research Project",
  "description": "Q4 2025 market analysis",
  "created_at": "2026-03-10T17:45:35Z",
  "updated_at": "2026-03-10T17:45:35Z"
}
```

**GET /projects/{project_id}**
- Get project details
- Response: 200 OK (same structure as POST response)

**GET /projects/{project_id}/files**
- List project files and directory structure
- Response: 200 OK
```json
{
  "nodes": [
    {
      "id": "node_123",
      "name": "reports",
      "type": "directory",
      "path": "/reports",
      "parent_id": null
    },
    {
      "id": "node_124",
      "name": "tesla-q4.md",
      "type": "file",
      "path": "/reports/tesla-q4.md",
      "size": 15420,
      "parent_id": "node_123",
      "created_at": "2026-03-10T18:00:00Z"
    }
  ]
}
```

**GET /projects/{project_id}/files/{file_path}**
- Download file content
- Response: 200 OK with file content

**POST /projects/{project_id}/files**
- Upload file to project
- Request: multipart/form-data with file and path
- Response: 201 Created

#### Conversations

**POST /conversations**
- Create new conversation
- Request:
```json
{
  "project_id": "proj_abc123",
  "title": "Research Tasks"
}
```
- Response: 201 Created
```json
{
  "id": "conv_xyz789",
  "project_id": "proj_abc123",
  "title": "Research Tasks",
  "created_at": "2026-03-10T17:45:35Z"
}
```

**GET /conversations/{conversation_id}**
- Get conversation details and messages
- Response: 200 OK
```json
{
  "id": "conv_xyz789",
  "project_id": "proj_abc123",
  "title": "Research Tasks",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "Research Tesla Q4 earnings",
      "created_at": "2026-03-10T17:46:00Z"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "I'll research Tesla's Q4 earnings and create a report.",
      "created_at": "2026-03-10T17:46:05Z"
    }
  ]
}
```

**POST /conversations/{conversation_id}/messages**
- Send message to conversation
- Request:
```json
{
  "content": "Research Tesla Q4 2025 earnings and create a report",
  "create_task": true,
  "skill": "research_report"
}
```
- Response: 201 Created
```json
{
  "message_id": "msg_003",
  "task_id": "task_456"
}
```

#### Tasks

**POST /tasks**
- Create task manually
- Request:
```json
{
  "conversation_id": "conv_xyz789",
  "project_id": "proj_abc123",
  "goal": "Research Tesla Q4 2025 earnings",
  "skill": "research_report",
  "model": "gpt-4-turbo-preview"
}
```
- Response: 201 Created
```json
{
  "id": "task_456",
  "conversation_id": "conv_xyz789",
  "project_id": "proj_abc123",
  "goal": "Research Tesla Q4 2025 earnings",
  "status": "pending",
  "skill": "research_report",
  "created_at": "2026-03-10T17:46:10Z"
}
```

**GET /tasks/{task_id}**
- Get task details
- Response: 200 OK
```json
{
  "id": "task_456",
  "conversation_id": "conv_xyz789",
  "project_id": "proj_abc123",
  "goal": "Research Tesla Q4 2025 earnings",
  "status": "running",
  "skill": "research_report",
  "current_run_id": "run_789",
  "created_at": "2026-03-10T17:46:10Z",
  "started_at": "2026-03-10T17:46:15Z"
}
```

**GET /tasks/{task_id}/runs**
- List all runs for a task
- Response: 200 OK
```json
{
  "runs": [
    {
      "id": "run_789",
      "task_id": "task_456",
      "status": "running",
      "started_at": "2026-03-10T17:46:15Z",
      "sandbox_id": "sandbox_abc"
    }
  ]
}
```

**POST /tasks/{task_id}/retry**
- Create new run for task
- Response: 201 Created
```json
{
  "run_id": "run_790",
  "status": "pending"
}
```

**POST /tasks/{task_id}/cancel**
- Cancel running task
- Response: 200 OK

#### Task Events (WebSocket)

**WS /tasks/{task_id}/events**
- Real-time task execution events
- Events:
```json
{
  "type": "run_started",
  "run_id": "run_789",
  "timestamp": "2026-03-10T17:46:15Z"
}

{
  "type": "step_started",
  "step_number": 1,
  "description": "Searching for Tesla Q4 earnings information",
  "timestamp": "2026-03-10T17:46:16Z"
}

{
  "type": "tool_called",
  "tool": "browser.open",
  "params": {"url": "https://ir.tesla.com"},
  "timestamp": "2026-03-10T17:46:17Z"
}

{
  "type": "tool_result",
  "tool": "browser.open",
  "result": {"success": true, "title": "Tesla Investor Relations"},
  "timestamp": "2026-03-10T17:46:20Z"
}

{
  "type": "artifact_created",
  "artifact_id": "art_123",
  "name": "tesla-q4-report.md",
  "type": "markdown",
  "timestamp": "2026-03-10T17:50:00Z"
}

{
  "type": "run_completed",
  "run_id": "run_789",
  "status": "success",
  "result": "Report generated successfully",
  "artifacts": ["art_123"],
  "timestamp": "2026-03-10T17:50:05Z"
}
```

#### Artifacts

**GET /artifacts/{artifact_id}**
- Get artifact metadata
- Response: 200 OK
```json
{
  "id": "art_123",
  "task_run_id": "run_789",
  "name": "tesla-q4-report.md",
  "type": "markdown",
  "size": 15420,
  "url": "/api/v1/artifacts/art_123/download",
  "created_at": "2026-03-10T17:50:00Z"
}
```

**GET /artifacts/{artifact_id}/download**
- Download artifact content
- Response: 200 OK with file content

**POST /artifacts/{artifact_id}/save-to-project**
- Save artifact to project directory
- Request:
```json
{
  "project_id": "proj_abc123",
  "path": "/reports/tesla-q4.md"
}
```
- Response: 201 Created

## 11. Success Criteria

### MVP Success Definition

The MVP is successful if a user can complete this end-to-end workflow:

1. Create a project
2. Start a conversation in that project
3. Request a complex task (e.g., "Research Tesla Q4 earnings and create a report")
4. See the agent execute multiple steps with real-time updates
5. View the generated artifact (report, code, etc.)
6. Save the artifact to the project directory
7. Initiate a follow-up task that references the previous work

### Functional Requirements

**Core Functionality:**
- ✅ User can create projects and view directory structure
- ✅ User can create conversations linked to projects
- ✅ User can send messages that trigger task creation
- ✅ System creates isolated sandbox for each task run
- ✅ Agent executes multi-step plans using available tools
- ✅ User sees real-time task progress and tool calls
- ✅ System generates artifacts (reports, code, screenshots)
- ✅ User can download artifacts
- ✅ User can save artifacts to project directory
- ✅ User can retry failed tasks
- ✅ System cleans up sandboxes after task completion

**Tool System:**
- ✅ Browser automation works (open, click, type, extract, screenshot)
- ✅ File operations work (list, read, write)
- ✅ Python code execution works with common libraries
- ✅ Web fetching works for API calls
- ✅ All tool calls are logged and visible to user

**RAG & Memory:**
- ✅ System can index and retrieve project files
- ✅ Agent can reference uploaded documents in tasks
- ✅ Conversation summaries are generated and stored
- ✅ Project-level facts are persisted across tasks

**Model Integration:**
- ✅ System supports OpenAI-compatible APIs
- ✅ System supports Anthropic API natively
- ✅ Users can configure default models
- ✅ Tasks can override model selection

### Quality Indicators

**Reliability:**
- Task success rate > 80% for well-defined goals
- Sandbox creation time < 10 seconds
- No data loss on task failure
- Graceful handling of tool errors

**Observability:**
- All tool calls logged with parameters and results
- Task state transitions tracked
- Error messages are actionable
- Execution time tracked per step

**User Experience:**
- Real-time updates appear within 1 second
- UI remains responsive during long-running tasks
- Clear error messages when tasks fail
- Intuitive project file browser

## 12. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Establish core infrastructure and basic task execution loop.

**Deliverables:**
- ✅ Database schema and models (project, conversation, message, task, task_run, sandbox_session, artifact)
- ✅ FastAPI backend with basic CRUD endpoints for projects and conversations
- ✅ Next.js frontend with project creation and conversation UI
- ✅ Docker sandbox manager with lifecycle management
- ✅ Basic agent orchestrator with plan-execute loop
- ✅ File tool implementation (list, read, write)
- ✅ Redis task queue setup
- ✅ Worker process that consumes tasks from queue

**Validation:**
- Can create project via API
- Can create conversation via API
- Can create task that spawns sandbox
- Agent can execute simple file operations in sandbox
- Sandbox cleans up after task completion

### Phase 2: Tool System & Real-time Updates (Weeks 3-4)

**Goal:** Implement full tool suite and real-time task monitoring.

**Deliverables:**
- ✅ Browser tools (open, click, type, extract, screenshot) using Playwright
- ✅ Python execution tool with common libraries
- ✅ Web fetch tool for HTTP requests
- ✅ Final answer tool for task completion
- ✅ WebSocket/SSE endpoint for task events
- ✅ Frontend real-time task status display
- ✅ Tool call logging and visualization
- ✅ Artifact storage in MinIO/S3
- ✅ Artifact download and preview in frontend

**Validation:**
- Agent can open browser, navigate, and extract data
- Agent can execute Python code and capture output
- Frontend shows real-time step updates
- User can view tool call parameters and results
- Screenshots and files saved as artifacts

### Phase 3: RAG, Memory & Skills (Weeks 5-6)

**Goal:** Add context awareness and task templates.

**Deliverables:**
- ✅ Document parser for PDF, Markdown, TXT
- ✅ pgvector integration for similarity search
- ✅ RAG indexer and retriever
- ✅ File upload to projects
- ✅ Conversation summary generation
- ✅ Project memory storage and retrieval
- ✅ Task working memory
- ✅ Three skill templates (research, webpage, analysis)
- ✅ Skill selection in task creation

**Validation:**
- User can upload PDF and ask questions about it
- Agent retrieves relevant context from project files
- Conversation summaries generated after N messages
- Skills customize agent behavior appropriately
- Follow-up tasks reference previous artifacts

### Phase 4: Model Abstraction & Polish (Weeks 7-8)

**Goal:** Multi-model support and production readiness.

**Deliverables:**
- ✅ Unified model interface abstraction
- ✅ OpenAI-compatible provider implementation
- ✅ Anthropic native provider implementation
- ✅ Embedding provider abstraction
- ✅ Model configuration and routing
- ✅ Task retry functionality
- ✅ Task cancellation
- ✅ Error handling and user-friendly messages
- ✅ Project file browser with save-artifact flow
- ✅ Docker Compose setup for easy deployment
- ✅ Documentation and setup guide

**Validation:**
- Can switch between OpenAI and Anthropic models
- Can configure default models via environment variables
- Task retry creates new run with fresh sandbox
- User can cancel long-running tasks
- Complete end-to-end workflow works smoothly
- Docker Compose brings up entire stack

## 13. Future Considerations

### Post-MVP Enhancements

**Multi-Agent Collaboration:**
- Parallel task execution with multiple agents
- Agent-to-agent communication protocols
- Task delegation and coordination
- Specialized agent roles (researcher, coder, analyst)

**Team Features:**
- User authentication and authorization
- Project sharing and permissions
- Team workspaces
- Activity feeds and notifications
- Commenting on tasks and artifacts

**Advanced Memory:**
- Graph-based knowledge representation
- Cross-project memory sharing
- Automatic fact extraction and linking
- Memory decay and relevance scoring

**Enhanced RAG:**
- Multi-modal document understanding (images, tables, charts)
- Semantic chunking strategies
- Hybrid search (keyword + vector)
- Citation tracking and source verification

**Platform Features:**
- Plugin marketplace for custom tools
- MCP (Model Context Protocol) deep integration
- Webhook integrations (Slack, GitHub, etc.)
- Scheduled/recurring tasks
- Task templates and workflows

**Deployment & Hosting:**
- One-click website deployment
- Custom domain support
- CDN integration
- Preview environments for artifacts
- Version control for project files

### Integration Opportunities

**Development Tools:**
- GitHub integration (create PRs, issues)
- GitLab, Bitbucket support
- Jira/Linear task sync
- VS Code extension

**Communication:**
- Slack bot for task initiation
- Discord integration
- Email notifications
- SMS alerts for task completion

**Data Sources:**
- Google Drive, Dropbox file sync
- Notion, Confluence knowledge bases
- Database connectors (MySQL, MongoDB)
- API integrations (REST, GraphQL)

**AI/ML Services:**
- Image generation (DALL-E, Midjourney)
- Speech-to-text for voice tasks
- Video processing capabilities
- Custom model fine-tuning

## 14. Risks & Mitigations

### Risk 1: Sandbox Escape or Security Vulnerabilities

**Impact:** High - Could compromise host system or leak sensitive data

**Mitigation:**
- Use Docker with strict security profiles (no privileged mode)
- Implement resource limits (CPU, memory, disk, network)
- Regular security audits of sandbox configuration
- Network isolation with whitelist-based egress rules
- Automatic sandbox termination after timeout
- Monitor sandbox behavior for anomalies

### Risk 2: Model API Costs Spiral Out of Control

**Impact:** Medium - Unexpected costs from long-running or inefficient tasks

**Mitigation:**
- Implement per-task token limits
- Track and display estimated costs in UI
- Set up billing alerts with cloud providers
- Cache common responses where appropriate
- Optimize prompts to reduce token usage
- Provide cost estimates before task execution

### Risk 3: Agent Gets Stuck in Infinite Loops

**Impact:** Medium - Wastes resources and provides poor user experience

**Mitigation:**
- Hard timeout on task execution (e.g., 10 minutes)
- Maximum step count per task (e.g., 50 steps)
- Detect repeated tool calls with same parameters
- Implement circuit breaker for failing tools
- Allow user to cancel tasks at any time
- Log loop detection events for debugging

### Risk 4: Poor Task Success Rate Undermines User Trust

**Impact:** High - Users abandon product if tasks frequently fail

**Mitigation:**
- Start with well-defined skill templates
- Provide clear task goal guidelines to users
- Implement robust error handling in tools
- Show detailed error messages and recovery suggestions
- Enable easy task retry with modified parameters
- Collect failure analytics to improve agent prompts
- Set realistic expectations about agent capabilities

### Risk 5: Artifact Storage Costs Grow Unbounded

**Impact:** Medium - Storage costs increase as users generate artifacts

**Mitigation:**
- Implement artifact retention policies (e.g., 30 days for unsaved)
- Compress artifacts where possible
- Deduplicate identical artifacts
- Provide user controls for artifact cleanup
- Archive old artifacts to cheaper storage tiers
- Set storage quotas per project

## 15. Appendix

### Related Documents

- **Original Requirements:** `docs/manus-mvp-requirements.md` - Detailed Chinese-language requirements document
- **Architecture Diagrams:** To be created in Phase 1
- **API Documentation:** Auto-generated via FastAPI OpenAPI at `/docs`
- **User Guide:** To be created in Phase 4

### Key Dependencies

**Core Infrastructure:**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Next.js](https://nextjs.org/) - React framework with App Router
- [PostgreSQL](https://www.postgresql.org/) - Relational database
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [Redis](https://redis.io/) - Task queue and cache
- [Docker](https://www.docker.com/) - Container runtime

**AI/ML:**
- [OpenAI API](https://platform.openai.com/docs/api-reference) - LLM provider
- [Anthropic API](https://docs.anthropic.com/) - Claude models
- [Playwright](https://playwright.dev/) - Browser automation

**Storage:**
- [MinIO](https://min.io/) - S3-compatible object storage
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS SDK for Python

### Repository Structure

```
manus-mvp/
├── README.md                 # Project overview and setup
├── docker-compose.yml        # Local development stack
├── .env.example              # Environment variable template
├── docs/                     # Documentation
│   ├── manus-mvp-requirements.md
│   ├── architecture.md
│   └── api.md
├── frontend/                 # Next.js application
├── backend/                  # FastAPI application
├── worker/                   # Task execution worker
├── shared/                   # Shared utilities
└── docker/                   # Docker configurations
```

### Data Model Summary

**Core Entities:**
1. `project` - Workspace for organizing tasks and files
2. `project_node` - File/directory in project tree
3. `conversation` - Chat interface for task initiation
4. `message` - Individual chat message
5. `task` - Logical task definition
6. `task_run` - Execution instance of a task
7. `sandbox_session` - Isolated execution environment
8. `artifact` - Generated file or output
9. `project_memory` - Project-level facts and context
10. `conversation_summary` - Conversation history summaries
11. `document_chunk` - RAG indexed content
12. `model_provider` - Model API configuration
13. `model_profile` - Model capabilities and settings

**Key Relationships:**
- `conversation` → many `task`
- `project` → many `task`
- `task` → many `task_run`
- `task_run` → one `sandbox_session`
- `task_run` → many `artifact`
- `project` → many `project_node`
- `project` → many `document_chunk`

### Glossary

- **Artifact:** A file or output generated during task execution (report, screenshot, code file)
- **Conversation:** Chat interface where users interact with the system and initiate tasks
- **Project:** Long-term workspace containing files, tasks, and context
- **Run:** A single execution instance of a task with its own sandbox
- **Sandbox:** Isolated Docker container where task tools execute
- **Skill:** Task template with predefined prompts, tools, and output formats
- **Task:** A goal-oriented unit of work executed by the agent
- **Tool:** A capability the agent can use (browser, file operations, code execution)
- **RAG:** Retrieval-Augmented Generation - retrieving relevant context from documents
- **Working Memory:** Temporary context maintained during task execution

---

**Document Version:** 1.0
**Last Updated:** 2026-03-10
**Status:** Draft for Review

