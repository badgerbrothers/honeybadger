# Feature: 数据库模式和模型

## Feature Description

创建Badgers MVP的完整SQLAlchemy数据模型层，包括8个核心实体模型、数据库连接管理和Alembic迁移系统。这是数据持久化的基础，为后续API开发提供ORM支持。

## User Story

作为开发人员
我想要有完整的SQLAlchemy模型定义和数据库迁移系统
以便我可以进行数据持久化、查询操作和数据库版本管理

## Problem Statement

当前项目只有占位符的database.py文件，没有实际的数据模型定义。需要：
- 定义8个核心实体模型（Project、ProjectNode、Conversation、Message、Task、TaskRun、SandboxSession、Artifact）
- 建立模型之间的关系（外键、一对多、多对多）
- 配置数据库连接和会话管理
- 设置Alembic迁移系统

## Solution Statement

使用SQLAlchemy 2.0的async API创建所有数据模型：
1. 配置异步数据库引擎和会话
2. 创建Base模型类
3. 实现8个实体模型，遵循PRD定义的资源边界
4. 配置Alembic进行数据库迁移管理
5. 创建初始迁移脚本

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium-High
**Primary Systems Affected**: Backend (Database Layer)
**Dependencies**: SQLAlchemy 2.0+, Alembic, asyncpg, PostgreSQL 15+

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**IMPORTANT: READ THESE BEFORE IMPLEMENTING!**

- `.claude/PRD.md` (Appendix section) - Data model summary and relationships
- `backend/app/database.py` - Current placeholder, needs full implementation
- `backend/app/config.py` - Database URL configuration
- `backend/pyproject.toml` - SQLAlchemy and Alembic dependencies already added
- `docs/implementation-plans.md` (lines 54-89) - Plan 1.2 requirements

### New Files to Create

**Models:**
- `backend/app/models/base.py` - Base model class with common fields
- `backend/app/models/project.py` - Project and ProjectNode models
- `backend/app/models/conversation.py` - Conversation and Message models
- `backend/app/models/task.py` - Task and TaskRun models
- `backend/app/models/sandbox.py` - SandboxSession model
- `backend/app/models/artifact.py` - Artifact model

**Database:**
- `backend/app/database.py` - Replace placeholder with full implementation
- `backend/alembic.ini` - Alembic configuration
- `backend/alembic/env.py` - Alembic environment setup
- `backend/alembic/versions/001_initial_schema.py` - Initial migration


### Relevant Documentation

**YOU SHOULD READ THESE BEFORE IMPLEMENTING!**

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
  - Async ORM usage
  - Why: Using async patterns for all database operations
- [SQLAlchemy Relationships](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
  - Defining relationships and foreign keys
  - Why: Multiple models have complex relationships
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
  - Migration setup and usage
  - Why: Need to set up migration system

### Patterns to Follow

**Naming Conventions:**
- Model classes: PascalCase (e.g., `ProjectNode`, `TaskRun`)
- Table names: snake_case (e.g., `project_nodes`, `task_runs`)
- Foreign keys: `{table}_id` (e.g., `project_id`, `task_id`)

**Model Structure:**
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

class ExampleModel(Base):
    __tablename__ = "example_models"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Async Database Pattern:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://...")
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```


---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Set up the base database infrastructure and common model patterns.

**Tasks:**
- Create Base model class with common fields (id, created_at, updated_at)
- Configure async database engine and session management
- Update database.py with proper async patterns
- Set up Alembic configuration files

### Phase 2: Core Implementation

Implement all 8 SQLAlchemy models with proper relationships.

**Tasks:**
- Create Project and ProjectNode models (tree structure with parent_id)
- Create Conversation and Message models (one-to-many)
- Create Task and TaskRun models (one-to-many with retry support)
- Create SandboxSession model (one-to-one with TaskRun)
- Create Artifact model (belongs to Project and TaskRun)
- Define all foreign key relationships and indexes

### Phase 3: Integration

Set up Alembic migrations and integrate models with the application.

**Tasks:**
- Initialize Alembic with proper configuration
- Create initial migration script for all tables
- Update models/__init__.py to export all models
- Test database connection and session creation

### Phase 4: Testing & Validation

Verify all models work correctly with database operations.

**Tasks:**
- Run Alembic migration to create tables
- Test CRUD operations for each model
- Verify foreign key constraints work
- Validate indexes are created correctly

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE backend/app/models/base.py

- **IMPLEMENT**: Base declarative class with common timestamp fields
- **PATTERN**: Use SQLAlchemy 2.0 Mapped and mapped_column syntax
- **IMPORTS**: 
  ```python
  from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
  from sqlalchemy import func
  from datetime import datetime
  import uuid
  ```
- **GOTCHA**: Use `func.now()` for server-side timestamps, not `datetime.utcnow()`
- **VALIDATE**: `cd backend && uv run python -c "from app.models.base import Base; print('Base model OK')"`

**Implementation:**
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
```


### CREATE backend/app/models/project.py

- **IMPLEMENT**: Project and ProjectNode models with tree structure
- **PATTERN**: ProjectNode uses self-referential foreign key for parent_id
- **IMPORTS**: `from sqlalchemy import String, Integer, ForeignKey, Text; from sqlalchemy.orm import relationship`
- **GOTCHA**: Use `back_populates` for bidirectional relationships
- **VALIDATE**: `cd backend && uv run python -c "from app.models.project import Project, ProjectNode; print('Project models OK')"`

**Implementation:**
```python
from sqlalchemy import String, Integer, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum
from .base import Base, TimestampMixin

class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    nodes: Mapped[list["ProjectNode"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="project")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="project")

class NodeType(enum.Enum):
    FILE = "file"
    DIRECTORY = "directory"

class ProjectNode(Base, TimestampMixin):
    __tablename__ = "project_nodes"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("project_nodes.id", ondelete="CASCADE"), nullable=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    node_type: Mapped[NodeType] = mapped_column(SQLEnum(NodeType), nullable=False)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # bytes, null for directories
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="nodes")
    parent: Mapped["ProjectNode | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["ProjectNode"]] = relationship(back_populates="parent")
```

### CREATE backend/app/models/conversation.py

- **IMPLEMENT**: Conversation and Message models
- **PATTERN**: One-to-many relationship (Conversation has many Messages)
- **IMPORTS**: Same as project.py plus `from sqlalchemy import Enum`
- **GOTCHA**: Message role should be enum (user/assistant/system)
- **VALIDATE**: `cd backend && uv run python -c "from app.models.conversation import Conversation, Message; print('Conversation models OK')"`

**Implementation:**
```python
from sqlalchemy import String, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum
from .base import Base, TimestampMixin

class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="conversation")

class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
```


### CREATE backend/app/models/task.py

- **IMPLEMENT**: Task and TaskRun models with retry support
- **PATTERN**: One-to-many (Task has many TaskRuns for retries)
- **IMPORTS**: Same as previous plus `from sqlalchemy import JSON`
- **GOTCHA**: TaskRun status should be enum; use JSON for metadata
- **VALIDATE**: `cd backend && uv run python -c "from app.models.task import Task, TaskRun; print('Task models OK')"`

**Implementation:**
```python
from sqlalchemy import String, ForeignKey, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum
from .base import Base, TimestampMixin

class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4-turbo-preview")
    current_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task_runs.id"), nullable=True)
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="tasks")
    project: Mapped["Project"] = relationship()
    runs: Mapped[list["TaskRun"]] = relationship(back_populates="task", cascade="all, delete-orphan", foreign_keys="TaskRun.task_id")

class TaskRun(Base, TimestampMixin):
    __tablename__ = "task_runs"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Relationships
    task: Mapped["Task"] = relationship(back_populates="runs", foreign_keys=[task_id])
    sandbox_session: Mapped["SandboxSession | None"] = relationship(back_populates="task_run")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="task_run")
```

### CREATE backend/app/models/sandbox.py

- **IMPLEMENT**: SandboxSession model for Docker container tracking
- **PATTERN**: One-to-one with TaskRun
- **IMPORTS**: Standard SQLAlchemy imports
- **GOTCHA**: Container ID should be indexed for quick lookups
- **VALIDATE**: `cd backend && uv run python -c "from app.models.sandbox import SandboxSession; print('Sandbox model OK')"`

**Implementation:**
```python
from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from .base import Base, TimestampMixin

class SandboxSession(Base, TimestampMixin):
    __tablename__ = "sandbox_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    container_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # millicores
    memory_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # MB
    terminated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    
    # Relationships
    task_run: Mapped["TaskRun"] = relationship(back_populates="sandbox_session")
```


### CREATE backend/app/models/artifact.py

- **IMPLEMENT**: Artifact model for generated outputs
- **PATTERN**: Belongs to both Project and TaskRun
- **IMPORTS**: Standard SQLAlchemy imports plus Enum
- **GOTCHA**: Storage path should be indexed; artifact_type is enum
- **VALIDATE**: `cd backend && uv run python -c "from app.models.artifact import Artifact; print('Artifact model OK')"`

**Implementation:**
```python
from sqlalchemy import String, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum
from .base import Base, TimestampMixin

class ArtifactType(enum.Enum):
    FILE = "file"
    SCREENSHOT = "screenshot"
    REPORT = "report"
    CODE = "code"
    DATA = "data"

class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(SQLEnum(ArtifactType), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship(back_populates="artifacts")
    task_run: Mapped["TaskRun"] = relationship(back_populates="artifacts")
```

### UPDATE backend/app/models/__init__.py

- **IMPLEMENT**: Export all models for easy imports
- **PATTERN**: Import all models and Base
- **IMPORTS**: All model classes from submodules
- **GOTCHA**: Import order matters for relationships
- **VALIDATE**: `cd backend && uv run python -c "from app.models import Base, Project, Task; print('Models import OK')"`

**Implementation:**
```python
"""SQLAlchemy models for Badgers MVP."""
from .base import Base, TimestampMixin
from .project import Project, ProjectNode, NodeType
from .conversation import Conversation, Message, MessageRole
from .task import Task, TaskRun, TaskStatus
from .sandbox import SandboxSession
from .artifact import Artifact, ArtifactType

__all__ = [
    "Base",
    "TimestampMixin",
    "Project",
    "ProjectNode",
    "NodeType",
    "Conversation",
    "Message",
    "MessageRole",
    "Task",
    "TaskRun",
    "TaskStatus",
    "SandboxSession",
    "Artifact",
    "ArtifactType",
]
```


### UPDATE backend/app/database.py

- **IMPLEMENT**: Replace placeholder with full async database setup
- **PATTERN**: Use async engine and session maker from SQLAlchemy 2.0
- **IMPORTS**: `from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker`
- **GOTCHA**: Use asyncpg driver (postgresql+asyncpg://), not psycopg2
- **VALIDATE**: `cd backend && uv run python -c "from app.database import engine, get_db; print('Database setup OK')"`

**Implementation:**
```python
"""Database connection and session management."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings
from .models.base import Base

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,  # Set to False in production
    pool_pre_ping=True,
)

# Create async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """Dependency for FastAPI to get database session."""
    async with async_session_maker() as session:
        yield session

async def init_db():
    """Initialize database tables (for development only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### CREATE backend/alembic.ini

- **IMPLEMENT**: Alembic configuration file
- **PATTERN**: Standard Alembic ini file with PostgreSQL
- **IMPORTS**: None (config file)
- **GOTCHA**: Use relative path for script_location
- **VALIDATE**: `cd backend && test -f alembic.ini && echo "alembic.ini created"`

**Implementation:**
```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```


### CREATE backend/alembic/env.py

- **IMPLEMENT**: Alembic environment configuration for async migrations
- **PATTERN**: Use async engine and run_sync for migrations
- **IMPORTS**: Import all models to ensure metadata is complete
- **GOTCHA**: Must import all models before accessing Base.metadata
- **VALIDATE**: `cd backend && test -f alembic/env.py && echo "env.py created"`

**Implementation:**
```python
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio

# Import app config and models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### CREATE backend/alembic/script.py.mako

- **IMPLEMENT**: Alembic migration template
- **PATTERN**: Standard Alembic template
- **IMPORTS**: None (template file)
- **GOTCHA**: This is a Mako template, not Python
- **VALIDATE**: `cd backend && test -f alembic/script.py.mako && echo "template created"`

**Implementation:**
```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```


### CREATE Initial Migration

- **IMPLEMENT**: Generate initial migration with all tables
- **PATTERN**: Use alembic revision --autogenerate
- **IMPORTS**: None (CLI command)
- **GOTCHA**: Ensure all models are imported in env.py before generating
- **VALIDATE**: `cd backend && uv run alembic revision --autogenerate -m "Initial schema" && echo "Migration created"`

**Command:**
```bash
cd backend
uv run alembic revision --autogenerate -m "Initial schema with all models"
```

### VERIFY Migration and Apply

- **IMPLEMENT**: Review generated migration and apply to database
- **PATTERN**: Check migration file, then run upgrade
- **IMPORTS**: None (CLI commands)
- **GOTCHA**: Review migration before applying; ensure PostgreSQL is running
- **VALIDATE**: `cd backend && uv run alembic upgrade head && echo "Migration applied"`

**Commands:**
```bash
# Review the generated migration file in alembic/versions/
cd backend
cat alembic/versions/*.py

# Apply migration
uv run alembic upgrade head
```

---

## TESTING STRATEGY

### Unit Tests

Create basic model tests to verify:
- Model instantiation works correctly
- Relationships are properly configured
- Enums serialize/deserialize correctly
- Timestamps are automatically set

**Test file**: `backend/tests/test_models.py`

**Test cases:**
```python
import pytest
from app.models import Project, ProjectNode, Conversation, Message, Task, TaskRun

@pytest.mark.asyncio
async def test_create_project(db_session):
    project = Project(name="Test Project", description="Test")
    db_session.add(project)
    await db_session.commit()
    assert project.id is not None
    assert project.created_at is not None

@pytest.mark.asyncio
async def test_project_node_tree(db_session):
    project = Project(name="Test")
    root = ProjectNode(project=project, name="root", path="/", node_type=NodeType.DIRECTORY)
    child = ProjectNode(project=project, parent=root, name="file.txt", path="/file.txt", node_type=NodeType.FILE)
    db_session.add_all([project, root, child])
    await db_session.commit()
    assert child.parent_id == root.id
```

### Integration Tests

Test database operations end-to-end:
- CRUD operations for each model
- Foreign key constraints work correctly
- Cascade deletes work as expected
- Indexes improve query performance

### Edge Cases

- Creating ProjectNode with invalid parent_id (should fail)
- Deleting Project cascades to all related entities
- TaskRun status transitions are valid
- Artifact storage_path uniqueness


---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Lint Python code
cd backend && uv run ruff check app/models/

# Check for type errors (if using mypy)
cd backend && uv run python -m mypy app/models/ --ignore-missing-imports
```

**Expected:** No linting errors, all type hints valid

### Level 2: Import Validation

```bash
# Verify all models can be imported
cd backend && uv run python -c "from app.models import Base, Project, ProjectNode, Conversation, Message, Task, TaskRun, SandboxSession, Artifact; print('All models imported successfully')"

# Verify database module works
cd backend && uv run python -c "from app.database import engine, get_db; print('Database module OK')"
```

**Expected:** All imports succeed without errors

### Level 3: Migration Validation

```bash
# Check Alembic configuration
cd backend && uv run alembic check

# Verify migration history
cd backend && uv run alembic current

# Test migration up and down
cd backend && uv run alembic downgrade -1
cd backend && uv run alembic upgrade head
```

**Expected:** Alembic commands execute without errors, migrations are reversible

### Level 4: Database Operations

```bash
# Start PostgreSQL if not running
docker-compose up -d postgres

# Apply migrations
cd backend && uv run alembic upgrade head

# Verify tables exist
cd backend && uv run python -c "
from sqlalchemy import inspect
from app.database import engine
import asyncio

async def check_tables():
    async with engine.connect() as conn:
        result = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        print('Tables:', result)
        expected = ['projects', 'project_nodes', 'conversations', 'messages', 'tasks', 'task_runs', 'sandbox_sessions', 'artifacts']
        assert all(t in result for t in expected), 'Missing tables'
        print('All tables created successfully')

asyncio.run(check_tables())
"
```

**Expected:** All 8 tables created in database

### Level 5: Unit Tests

```bash
# Run model tests (after creating test file)
cd backend && uv run pytest tests/test_models.py -v
```

**Expected:** All tests pass


---

## ACCEPTANCE CRITERIA

- [ ] All 8 models created with correct fields and types
- [ ] All relationships properly defined with back_populates
- [ ] Foreign keys have appropriate ondelete cascades
- [ ] Enums defined for status, role, type fields
- [ ] Timestamps (created_at, updated_at) on all models
- [ ] Database.py uses async SQLAlchemy 2.0 patterns
- [ ] Alembic configured with async support
- [ ] Initial migration generated and applied successfully
- [ ] All validation commands pass with zero errors
- [ ] Can create, read, update, delete records for each model
- [ ] Foreign key constraints enforced by database
- [ ] Cascade deletes work correctly (deleting Project removes all related data)
- [ ] No linting or type checking errors
- [ ] Code follows project naming conventions (snake_case tables, PascalCase models)

---

## COMPLETION CHECKLIST

- [ ] All model files created in backend/app/models/
- [ ] base.py with Base and TimestampMixin
- [ ] project.py with Project and ProjectNode
- [ ] conversation.py with Conversation and Message
- [ ] task.py with Task and TaskRun
- [ ] sandbox.py with SandboxSession
- [ ] artifact.py with Artifact
- [ ] models/__init__.py exports all models
- [ ] database.py updated with async engine and session
- [ ] alembic.ini configuration file created
- [ ] alembic/env.py with async migration support
- [ ] alembic/script.py.mako template created
- [ ] Initial migration generated with alembic revision
- [ ] Migration reviewed and looks correct
- [ ] Migration applied with alembic upgrade head
- [ ] All 8 tables exist in PostgreSQL database
- [ ] All validation commands executed successfully
- [ ] Import validation passes
- [ ] Alembic check passes
- [ ] Database operations work correctly
- [ ] Ready for Plan 1.3 (Pydantic Schemas)

---

## NOTES

**Design Decisions:**

1. **UUID Primary Keys**: Using UUID instead of auto-incrementing integers for better distributed system support and security (no enumeration attacks).

2. **Server-side Timestamps**: Using `func.now()` instead of `datetime.utcnow()` ensures timestamps are consistent with database server time, avoiding clock skew issues.

3. **Async Throughout**: All database operations use async/await patterns for better concurrency and performance with FastAPI.

4. **Cascade Deletes**: Projects cascade delete to all related entities (nodes, conversations, tasks, artifacts) to maintain referential integrity.

5. **Task-Run Separation**: Tasks are reusable definitions; TaskRuns are execution instances. This enables retry without duplicating task configuration.

6. **Enum Types**: Using Python enums mapped to PostgreSQL enum types for type safety and database-level validation.

7. **JSON Fields**: TaskRun.logs uses JSON type for flexible log storage without schema changes.

**Trade-offs:**

- **asyncpg vs psycopg2**: Using asyncpg for async support, but requires PostgreSQL (no SQLite support). This is acceptable for MVP as PostgreSQL is required anyway.

- **Alembic Complexity**: Async Alembic setup is more complex than sync, but necessary for consistency with application code.

- **No Soft Deletes**: Using hard deletes for simplicity in MVP. Can add soft delete pattern later if needed.

**Future Considerations:**

- Add indexes on frequently queried fields (project_id, task_id, status)
- Consider partitioning for large tables (messages, artifacts)
- Add full-text search indexes for content fields
- Implement audit logging for sensitive operations
- Add database connection pooling configuration

