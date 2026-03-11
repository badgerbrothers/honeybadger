# Feature: Pydantic Schemas

## Feature Description

为 Badgers MVP 的所有资源创建完整的 Pydantic schemas，用于 FastAPI 的请求验证和响应序列化。包括 Project、Conversation、Message、Task、TaskRun、SandboxSession 和 Artifact 的 Create、Update、Response schemas。

## User Story

作为开发人员
我想要有完整的 Pydantic schema 定义
以便我可以进行 API 请求验证、响应序列化和自动生成 API 文档

## Problem Statement

当前项目只有 SQLAlchemy 模型，没有 Pydantic schemas。需要：
- 为每个资源创建 Create、Update、Response schemas
- 实现字段验证和类型检查
- 支持 FastAPI 的自动文档生成
- 遵循 PRD 定义的资源边界

## Solution Statement

使用 Pydantic v2 创建所有 schemas：
1. 为每个资源创建独立的 schema 文件
2. 分离 Create（输入）、Update（部分更新）、Response（输出）schemas
3. 使用 ConfigDict 配置 from_attributes 支持 ORM 模型转换
4. 添加字段验证器和文档字符串

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: Backend (API Layer)
**Dependencies**: Pydantic v2.0+

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**IMPORTANT: READ THESE BEFORE IMPLEMENTING!**

- `backend/app/models/project.py` - Project 和 ProjectNode 模型结构
- `backend/app/models/conversation.py` - Conversation 和 Message 模型
- `backend/app/models/task.py` - Task 和 TaskRun 模型
- `backend/app/models/sandbox.py` - SandboxSession 模型
- `backend/app/models/artifact.py` - Artifact 模型
- `docs/implementation-plans.md` (lines 93-125) - Plan 1.3 要求
- `.claude/PRD.md` - API 规范和资源边界定义

### New Files to Create

**Schemas:**
- `backend/app/schemas/project.py` - Project 和 ProjectNode schemas
- `backend/app/schemas/conversation.py` - Conversation 和 Message schemas
- `backend/app/schemas/task.py` - Task 和 TaskRun schemas
- `backend/app/schemas/sandbox.py` - SandboxSession schemas
- `backend/app/schemas/artifact.py` - Artifact schemas
- `backend/app/schemas/__init__.py` - 导出所有 schemas

### Relevant Documentation

**YOU SHOULD READ THESE BEFORE IMPLEMENTING!**

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
  - Models and validation
  - Why: Using Pydantic v2 syntax
- [Pydantic ConfigDict](https://docs.pydantic.dev/latest/api/config/)
  - from_attributes configuration
  - Why: Need to convert SQLAlchemy models to Pydantic
- [FastAPI with Pydantic](https://fastapi.tiangolo.com/tutorial/body/)
  - Request and response models
  - Why: Integration with FastAPI


### Patterns to Follow

**Naming Conventions:**
- Schema classes: PascalCase with suffix (e.g., `ProjectCreate`, `ProjectResponse`)
- Create schemas: `{Resource}Create` (for POST requests)
- Update schemas: `{Resource}Update` (for PATCH/PUT requests)
- Response schemas: `{Resource}Response` (for API responses)

**Pydantic v2 Pattern:**
```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid

class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, description="Project description")

class ProjectResponse(BaseModel):
    """Schema for project API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
```

**Field Validation:**
- Use `Field()` for constraints and documentation
- Use `min_length`, `max_length` for strings
- Use `ge`, `le` for numbers
- Add `description` for API documentation

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create base schema patterns and common utilities.

**Tasks:**
- Set up schema directory structure
- Define common base schemas if needed
- Import and configure Pydantic v2

### Phase 2: Core Implementation

Implement all resource schemas.

**Tasks:**
- Create Project and ProjectNode schemas
- Create Conversation and Message schemas
- Create Task and TaskRun schemas
- Create SandboxSession schemas
- Create Artifact schemas

### Phase 3: Integration

Export and organize schemas for easy import.

**Tasks:**
- Update schemas/__init__.py to export all schemas
- Verify schema imports work correctly

### Phase 4: Testing & Validation

Verify schemas work correctly.

**Tasks:**
- Test schema validation
- Test ORM model conversion
- Verify all fields serialize correctly

---

## STEP-BY-STEP TASKS

### CREATE backend/app/schemas/__init__.py

- **IMPLEMENT**: Create schemas directory and __init__.py file
- **PATTERN**: Empty file initially, will add exports later
- **VALIDATE**: `ls backend/app/schemas/__init__.py`

### CREATE backend/app/schemas/project.py

- **IMPLEMENT**: ProjectCreate, ProjectUpdate, ProjectResponse schemas
- **IMPLEMENT**: ProjectNodeCreate, ProjectNodeUpdate, ProjectNodeResponse schemas
- **PATTERN**: Follow PRD Section 7.1 - Projects API specification
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict, Field`
- **IMPORTS**: `from datetime import datetime`
- **IMPORTS**: `import uuid`
- **IMPORTS**: `from app.models.project import NodeType`
- **FIELDS**:
  - ProjectCreate: name (str, 1-255), description (str | None)
  - ProjectUpdate: name (str | None, 1-255), description (str | None)
  - ProjectResponse: id, name, description, created_at, updated_at
  - ProjectNodeCreate: name (str, 1-255), node_type (NodeType), parent_id (uuid | None), content (str | None)
  - ProjectNodeUpdate: name (str | None), content (str | None)
  - ProjectNodeResponse: id, project_id, parent_id, name, node_type, content, created_at, updated_at
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas.project import ProjectCreate, ProjectResponse"`

### CREATE backend/app/schemas/conversation.py

- **IMPLEMENT**: ConversationCreate, ConversationUpdate, ConversationResponse schemas
- **IMPLEMENT**: MessageCreate, MessageResponse schemas (no MessageUpdate - messages are immutable)
- **PATTERN**: Follow PRD Section 7.2 - Conversations API specification
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict, Field`
- **IMPORTS**: `from datetime import datetime`
- **IMPORTS**: `import uuid`
- **IMPORTS**: `from app.models.conversation import MessageRole`
- **FIELDS**:
  - ConversationCreate: title (str | None, max 255)
  - ConversationUpdate: title (str | None, max 255)
  - ConversationResponse: id, project_id, title, created_at, updated_at
  - MessageCreate: role (MessageRole), content (str, min 1)
  - MessageResponse: id, conversation_id, role, content, created_at
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas.conversation import ConversationCreate, MessageCreate"`

### CREATE backend/app/schemas/task.py

- **IMPLEMENT**: TaskCreate, TaskUpdate, TaskResponse schemas
- **IMPLEMENT**: TaskRunCreate, TaskRunResponse schemas (no TaskRunUpdate - runs are immutable)
- **PATTERN**: Follow PRD Section 7.3 - Tasks API specification
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict, Field`
- **IMPORTS**: `from datetime import datetime`
- **IMPORTS**: `import uuid`
- **IMPORTS**: `from app.models.task import TaskStatus`
- **FIELDS**:
  - TaskCreate: goal (str, min 1), skill_name (str | None, max 100)
  - TaskUpdate: goal (str | None, min 1)
  - TaskResponse: id, conversation_id, goal, skill_name, status, current_run_id, created_at, updated_at
  - TaskRunCreate: No fields (runs are created by system)
  - TaskRunResponse: id, task_id, sandbox_session_id, status, started_at, completed_at, error_message
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas.task import TaskCreate, TaskResponse"`

### CREATE backend/app/schemas/sandbox.py

- **IMPLEMENT**: SandboxSessionResponse schema only (no Create/Update - managed by system)
- **PATTERN**: Follow PRD Section 7.4 - Sandbox Sessions API specification
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict, Field`
- **IMPORTS**: `from datetime import datetime`
- **IMPORTS**: `import uuid`
- **FIELDS**:
  - SandboxSessionResponse: id, project_id, container_id, status, created_at, terminated_at
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas.sandbox import SandboxSessionResponse"`

### CREATE backend/app/schemas/artifact.py

- **IMPLEMENT**: ArtifactCreate, ArtifactResponse schemas (no ArtifactUpdate - artifacts are immutable)
- **PATTERN**: Follow PRD Section 7.5 - Artifacts API specification
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict, Field`
- **IMPORTS**: `from datetime import datetime`
- **IMPORTS**: `import uuid`
- **IMPORTS**: `from app.models.artifact import ArtifactType`
- **FIELDS**:
  - ArtifactCreate: name (str, 1-255), artifact_type (ArtifactType), storage_path (str, 1-1024), size (int, ge=0), mime_type (str | None, max 100)
  - ArtifactResponse: id, project_id, task_run_id, name, artifact_type, storage_path, size, mime_type, created_at
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas.artifact import ArtifactCreate, ArtifactResponse"`

### UPDATE backend/app/schemas/__init__.py

- **IMPLEMENT**: Export all schemas for easy import
- **PATTERN**: Import and re-export all schema classes
- **IMPORTS**: Import all Create, Update, Response schemas from each module
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas import ProjectCreate, ConversationCreate, TaskCreate"`

---

## TESTING STRATEGY

This feature focuses on schema definitions without business logic. Testing will validate:
1. Schema instantiation and validation
2. Field constraints (min/max length, required fields)
3. ORM model conversion (from_attributes)

### Unit Tests

Create `backend/tests/test_schemas.py` with tests for each schema:

**Test Categories:**
- **Validation Tests**: Verify Field constraints work (min_length, max_length, ge)
- **Serialization Tests**: Verify schemas can serialize from SQLAlchemy models
- **Type Tests**: Verify correct types are enforced

**Example Test Structure:**
```python
def test_project_create_valid():
    schema = ProjectCreate(name="Test", description="Desc")
    assert schema.name == "Test"

def test_project_create_name_too_short():
    with pytest.raises(ValidationError):
        ProjectCreate(name="", description="Desc")

def test_project_response_from_model(db_session):
    project = Project(name="Test", description="Desc")
    response = ProjectResponse.model_validate(project)
    assert response.name == "Test"
```

### Integration Tests

Not required for this feature - schemas will be tested through API endpoint tests in future plans.

### Edge Cases

- Empty strings for required fields
- Strings exceeding max_length
- Invalid enum values
- None values for required fields
- UUID format validation

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd backend && uv run ruff check app/schemas/
```

**Expected**: No errors, all files pass linting

### Level 2: Import Validation

```bash
cd backend && uv run python -c "from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectNodeCreate, ProjectNodeUpdate, ProjectNodeResponse, ConversationCreate, ConversationUpdate, ConversationResponse, MessageCreate, MessageResponse, TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse, SandboxSessionResponse, ArtifactCreate, ArtifactResponse"
```

**Expected**: No import errors, all schemas load successfully

### Level 3: Schema Instantiation

```bash
cd backend && uv run python -c "
from app.schemas.project import ProjectCreate
p = ProjectCreate(name='Test Project', description='Test')
print(f'✓ ProjectCreate: {p.name}')
"
```

**Expected**: Schema instantiates correctly, prints "✓ ProjectCreate: Test Project"

### Level 4: Unit Tests

```bash
cd backend && uv run pytest tests/test_schemas.py -v
```

**Expected**: All schema tests pass

### Level 5: Type Checking (Optional)

```bash
cd backend && uv run mypy app/schemas/ --ignore-missing-imports
```

**Expected**: No type errors (if mypy is configured)

---

## ACCEPTANCE CRITERIA

- [ ] All 5 schema files created (project.py, conversation.py, task.py, sandbox.py, artifact.py)
- [ ] All schemas follow Pydantic v2 syntax with ConfigDict
- [ ] Create schemas defined for: Project, ProjectNode, Conversation, Message, Task, Artifact
- [ ] Update schemas defined for: Project, ProjectNode, Conversation, Task
- [ ] Response schemas defined for all 7 resources
- [ ] All Field constraints match PRD specifications (min_length, max_length, etc.)
- [ ] All schemas use proper type hints (str | None for optional fields)
- [ ] Enum imports work correctly (NodeType, MessageRole, TaskStatus, ArtifactType)
- [ ] schemas/__init__.py exports all schemas
- [ ] All validation commands pass with zero errors
- [ ] Schemas can instantiate with valid data
- [ ] Schemas reject invalid data (empty strings, exceeding max_length)
- [ ] Response schemas have from_attributes=True for ORM conversion

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] backend/app/schemas/ directory created
- [ ] All 5 schema files created and importable
- [ ] schemas/__init__.py exports all schemas
- [ ] Ruff linting passes with zero errors
- [ ] All schemas can be imported without errors
- [ ] Schema instantiation tests pass
- [ ] Unit tests created and passing
- [ ] All acceptance criteria met
- [ ] Ready for API router integration (Plan 1.4)

---

## NOTES

**Design Decisions:**

1. **No Update schemas for immutable resources**: Message, TaskRun, Artifact, and SandboxSession are immutable after creation, so no Update schemas needed.

2. **Minimal Create schemas**: TaskRunCreate and SandboxSessionCreate are not needed as these resources are created by the system, not by user API calls.

3. **Enum imports**: Import enums from models (NodeType, MessageRole, TaskStatus, ArtifactType) to maintain single source of truth.

4. **Field validation**: Use Pydantic Field() with constraints matching PRD specifications exactly (e.g., name max_length=255).

5. **from_attributes**: Only Response schemas need ConfigDict(from_attributes=True) for ORM conversion. Create/Update schemas don't need this.

**Implementation Order Rationale:**

- Create schemas in dependency order (Project → Conversation → Task → Sandbox → Artifact)
- Each schema file is independent and can be tested immediately after creation
- __init__.py updated last to export all schemas at once

**Future Considerations:**

- These schemas will be used in API routers (Plan 1.4)
- Response schemas may need nested relationships later (e.g., ProjectResponse with nodes list)
- Consider adding custom validators for complex business rules in future iterations

