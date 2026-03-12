# Feature: Memory System (Plan 3.4)

## Feature Description

Implement a comprehensive memory system for the Badgers MVP platform that enables:
1. **Conversation Summarization** - Compress long conversation histories into concise summaries
2. **Project Memory** - Store persistent project-level knowledge, facts, and preferences
3. **Task Working Memory** - Maintain temporary context during task execution

This system will improve agent performance by providing relevant context while managing token limits, enable knowledge persistence across sessions, and support more intelligent task execution.

## User Story

As a user
I want the agent to remember important information from past conversations and tasks
So that I don't have to repeat context and the agent can make better decisions based on accumulated knowledge

## Problem Statement

Currently, the system stores raw conversation messages and task logs but lacks:
- Context compression for long conversations (leading to token limit issues)
- Persistent project-level knowledge extraction and retrieval
- Structured working memory for task execution context
- Semantic search over accumulated knowledge

This limits the agent's ability to maintain context over long interactions and leverage past learnings.

## Solution Statement

Implement a three-tier memory system:
1. **Conversation summaries** - Periodically compress message history using LLM summarization
2. **Project memory** - Extract and store key facts with vector embeddings for semantic retrieval
3. **Task working memory** - Structure TaskRun logs to maintain execution context

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: Backend (models, routers, services), Worker (agent orchestrator)
**Dependencies**: OpenAI API (for summarization), pgvector (for embeddings)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - MUST READ BEFORE IMPLEMENTING!

- `backend/app/models/conversation.py` (lines 14-35) - Current Conversation and Message models
- `backend/app/models/task.py` (lines 17-49) - Task and TaskRun models with logs field
- `backend/app/models/document_chunk.py` (lines 8-20) - pgvector pattern for embeddings
- `backend/app/models/project.py` (lines 8-25) - Project model structure
- `backend/app/routers/conversations.py` (lines 57-74) - Message retrieval patterns
- `backend/app/routers/tasks.py` (lines 18-76) - Task management endpoints
- `backend/rag/embeddings.py` (lines 1-50) - EmbeddingService for vector generation
- `backend/rag/retriever.py` (lines 15-65) - Vector similarity search pattern
- `worker/orchestrator/agent.py` (lines 25-69) - Agent message history management

### New Files to Create

- `backend/app/models/memory.py` - ConversationSummary and ProjectMemory models
- `backend/app/schemas/memory.py` - Pydantic schemas for memory operations
- `backend/app/routers/memory.py` - API endpoints for memory management
- `backend/app/services/memory_service.py` - Memory extraction and summarization logic
- `backend/alembic/versions/003_memory_system.py` - Database migration
- `backend/tests/test_api_memory.py` - Memory API tests
- `backend/tests/test_memory_service.py` - Memory service unit tests

### Relevant Documentation - READ BEFORE IMPLEMENTING!

- [OpenAI Chat Completions](https://platform.openai.com/docs/guides/chat-completions)
  - Section: Function calling and structured outputs
  - Why: For extracting structured memory facts
- [pgvector Documentation](https://github.com/pgvector/pgvector#querying)
  - Section: Similarity search queries
  - Why: For semantic memory retrieval
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
  - Section: Async session patterns
  - Why: Consistent with existing database patterns

### Patterns to Follow

**Model Pattern** (from `backend/app/models/conversation.py`):
```python
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
```

**Vector Embedding Pattern** (from `backend/app/models/document_chunk.py`):
```python
from pgvector.sqlalchemy import Vector

class DocumentChunk(Base):
    embedding = Column(Vector(1536))  # OpenAI embedding dimension
```

**Service Pattern** (from `backend/rag/embeddings.py`):
```python
class EmbeddingService:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]
```

**Router Pattern** (from `backend/app/routers/conversations.py`):
```python
router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    )
    return result.scalars().all()
```

**Error Handling Pattern**:
```python
try:
    # operation
    await db.commit()
except Exception as e:
    await db.rollback()
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## IMPLEMENTATION PLAN

### Phase 1: Database Models and Migration

Create memory-related database models and migration script.

**Tasks:**
- Define ConversationSummary model with summary text and metadata
- Define ProjectMemory model with vector embeddings
- Create Alembic migration for new tables
- Add indexes for efficient querying

### Phase 2: Memory Service Layer

Implement core memory extraction and summarization logic.

**Tasks:**
- Create MemoryService for summarization using OpenAI
- Implement conversation summarization logic
- Implement memory fact extraction from conversations
- Add vector embedding generation for memories

### Phase 3: API Endpoints

Create REST API endpoints for memory operations.

**Tasks:**
- Add conversation summary endpoints (create, retrieve)
- Add project memory endpoints (create, list, search)
- Add task working memory endpoints (update, retrieve)
- Implement semantic search for memories

### Phase 4: Worker Integration

Integrate memory system with agent orchestrator.

**Tasks:**
- Modify agent to load relevant memories before execution
- Add memory extraction after task completion
- Implement automatic summarization triggers
- Update task run logs structure

### Phase 5: Testing and Validation

Comprehensive testing of memory system.

**Tasks:**
- Unit tests for memory service
- Integration tests for API endpoints
- Test summarization quality
- Test memory retrieval accuracy

---

## STEP-BY-STEP TASKS

### CREATE backend/app/models/memory.py

- **IMPLEMENT**: ConversationSummary model
  - Fields: id, conversation_id, summary_text, message_count, created_at
  - Relationship to Conversation
- **IMPLEMENT**: ProjectMemory model
  - Fields: id, project_id, memory_type, content, embedding (Vector), metadata (JSON), created_at
  - Relationship to Project
  - Index on embedding for similarity search
- **PATTERN**: Follow model structure from `conversation.py` lines 14-35
- **IMPORTS**: `from pgvector.sqlalchemy import Vector`
- **VALIDATE**: `uv run python -c "from app.models.memory import ConversationSummary, ProjectMemory"`


### CREATE backend/app/schemas/memory.py

- **IMPLEMENT**: ConversationSummaryCreate schema (conversation_id, summary_text, message_count)
- **IMPLEMENT**: ConversationSummaryResponse schema (add id, created_at)
- **IMPLEMENT**: ProjectMemoryCreate schema (project_id, memory_type, content, metadata)
- **IMPLEMENT**: ProjectMemoryResponse schema (add id, created_at, exclude embedding)
- **IMPLEMENT**: ProjectMemorySearch schema (query, limit, threshold)
- **PATTERN**: Follow schema structure from `conversation.py` lines 8-35
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict`
- **VALIDATE**: `uv run python -c "from app.schemas.memory import ConversationSummaryCreate"`

### CREATE backend/alembic/versions/003_memory_system.py

- **IMPLEMENT**: Migration to create conversation_summaries table
- **IMPLEMENT**: Migration to create project_memories table with vector column
- **IMPLEMENT**: Add indexes: conversation_id, project_id, embedding (ivfflat)
- **PATTERN**: Follow migration structure from `001_pgvector.py`
- **IMPORTS**: `from pgvector.sqlalchemy import Vector`
- **GOTCHA**: Must enable pgvector extension before creating vector columns
- **VALIDATE**: `cd backend && uv run alembic upgrade head`

### CREATE backend/app/services/memory_service.py

- **IMPLEMENT**: MemoryService class with OpenAI client
- **IMPLEMENT**: `summarize_conversation(messages: list[Message]) -> str` method
  - Use OpenAI to generate concise summary
  - Include key topics, decisions, and action items
- **IMPLEMENT**: `extract_memory_facts(conversation_id: UUID, db: AsyncSession) -> list[dict]` method
  - Extract key facts from conversation
  - Generate embeddings for each fact
- **IMPLEMENT**: `search_memories(project_id: UUID, query: str, limit: int) -> list[ProjectMemory]` method
  - Generate query embedding
  - Perform vector similarity search
- **PATTERN**: Follow EmbeddingService pattern from `rag/embeddings.py`
- **IMPORTS**: `from openai import AsyncOpenAI`, `from app.models.memory import ProjectMemory`
- **VALIDATE**: `uv run pytest tests/test_memory_service.py -v`

### CREATE backend/app/routers/memory.py

- **IMPLEMENT**: POST `/api/conversations/{id}/summarize` endpoint
  - Fetch messages, generate summary, store in DB
  - Return ConversationSummaryResponse
- **IMPLEMENT**: GET `/api/conversations/{id}/summary` endpoint
  - Retrieve latest summary for conversation
- **IMPLEMENT**: POST `/api/projects/{id}/memories` endpoint
  - Create new project memory with embedding
- **IMPLEMENT**: GET `/api/projects/{id}/memories` endpoint
  - List all memories for project
- **IMPLEMENT**: POST `/api/projects/{id}/memories/search` endpoint
  - Semantic search over project memories
- **PATTERN**: Follow router structure from `conversations.py`
- **IMPORTS**: `from app.services.memory_service import memory_service`
- **VALIDATE**: `uv run pytest tests/test_api_memory.py -v`

### UPDATE backend/app/main.py

- **ADD**: Import memory router
- **ADD**: `app.include_router(memory.router)` after other routers
- **PATTERN**: Lines 4-21 show router registration pattern
- **VALIDATE**: `uv run python -c "from app.main import app; print(app.routes)"`


### UPDATE backend/app/models/task.py

- **ADD**: `working_memory` field to TaskRun model (JSON type)
- **IMPLEMENT**: Structure for working_memory: {context, tool_history, intermediate_results}
- **PATTERN**: Follow existing `logs` field pattern at line 44
- **VALIDATE**: `uv run python -c "from app.models.task import TaskRun; print(TaskRun.__table__.columns)"`

### UPDATE worker/orchestrator/agent.py

- **ADD**: Load project memories before task execution
- **IMPLEMENT**: `_load_project_context(project_id: UUID) -> str` method
  - Fetch relevant project memories
  - Format as context string for system prompt
- **ADD**: Extract and save memories after task completion
- **IMPLEMENT**: `_extract_task_memories(task_run_id: UUID)` method
  - Extract key learnings from task execution
  - Save to project memories
- **PATTERN**: Follow message history pattern at lines 25-69
- **IMPORTS**: `from app.services.memory_service import memory_service`
- **VALIDATE**: `uv run pytest worker/tests/test_agent.py -v -k memory`

### CREATE backend/tests/test_memory_service.py

- **IMPLEMENT**: Test conversation summarization
- **IMPLEMENT**: Test memory fact extraction
- **IMPLEMENT**: Test semantic memory search
- **IMPLEMENT**: Mock OpenAI API calls
- **PATTERN**: Follow test structure from `test_embeddings.py`
- **IMPORTS**: `from unittest.mock import AsyncMock, patch`
- **VALIDATE**: `uv run pytest tests/test_memory_service.py -v --cov=app.services.memory_service`

### CREATE backend/tests/test_api_memory.py

- **IMPLEMENT**: Test POST /api/conversations/{id}/summarize
- **IMPLEMENT**: Test GET /api/conversations/{id}/summary
- **IMPLEMENT**: Test POST /api/projects/{id}/memories
- **IMPLEMENT**: Test GET /api/projects/{id}/memories
- **IMPLEMENT**: Test POST /api/projects/{id}/memories/search
- **PATTERN**: Follow test structure from `test_api_conversations.py`
- **IMPORTS**: `from httpx import AsyncClient, ASGITransport`
- **VALIDATE**: `uv run pytest tests/test_api_memory.py -v`

---

## TESTING STRATEGY

### Unit Tests

**Memory Service Tests** (`tests/test_memory_service.py`):
- Mock OpenAI API responses for summarization
- Test conversation summarization with various message counts
- Test memory fact extraction logic
- Test vector similarity search
- Test error handling for API failures

**Expected Coverage**: 80%+ for memory_service.py

### Integration Tests

**Memory API Tests** (`tests/test_api_memory.py`):
- Test full conversation summarization workflow
- Test memory creation with embedding generation
- Test semantic search with actual vector operations
- Test memory retrieval and filtering
- Test error cases (non-existent conversation, invalid project)

**Expected Coverage**: 80%+ for routers/memory.py

### Edge Cases

- Empty conversation summarization
- Very long conversations (>100 messages)
- Duplicate memory facts
- Low similarity threshold searches (no results)
- Concurrent memory creation
- Memory search with special characters in query

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd backend && uv run ruff check app/models/memory.py app/schemas/memory.py app/routers/memory.py app/services/memory_service.py
```

**Expected**: All checks passed!

### Level 2: Database Migration

```bash
cd backend && uv run alembic upgrade head
```

**Expected**: Migration applies successfully, tables created

### Level 3: Unit Tests

```bash
cd backend && uv run pytest tests/test_memory_service.py tests/test_api_memory.py -v
```

**Expected**: All tests pass

### Level 4: Integration Tests

```bash
cd backend && uv run pytest tests/test_api_memory.py -v --cov=app.routers.memory --cov=app.services.memory_service
```

**Expected**: All tests pass, coverage >= 80%

### Level 5: Manual Validation

```bash
# Start backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Test conversation summarization
curl -X POST http://localhost:8000/api/conversations/{conversation_id}/summarize

# Test memory search
curl -X POST http://localhost:8000/api/projects/{project_id}/memories/search \
  -H "Content-Type: application/json" \
  -d '{"query": "user preferences", "limit": 5}'
```

**Expected**: Valid JSON responses, summaries are coherent, search returns relevant results


---

## ACCEPTANCE CRITERIA

- [ ] ConversationSummary and ProjectMemory models created with proper relationships
- [ ] Database migration applies successfully with vector indexes
- [ ] MemoryService can generate conversation summaries using OpenAI
- [ ] MemoryService can extract and embed memory facts
- [ ] Semantic search returns relevant memories based on query
- [ ] All API endpoints return correct response schemas
- [ ] Agent loads project memories before task execution
- [ ] Agent extracts memories after task completion
- [ ] TaskRun working_memory field stores structured context
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage >= 80% for new code
- [ ] Integration tests verify end-to-end workflows
- [ ] Manual testing confirms summaries are coherent and relevant
- [ ] No regressions in existing conversation/task functionality

---

## COMPLETION CHECKLIST

- [ ] All database models created and migrated
- [ ] All Pydantic schemas defined
- [ ] MemoryService implemented with OpenAI integration
- [ ] All API endpoints implemented and tested
- [ ] Worker agent integration completed
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Linting passes with no errors
- [ ] Manual validation confirms feature works
- [ ] Code follows project conventions
- [ ] Documentation updated (if needed)

---

## NOTES

### Design Decisions

**1. Conversation Summarization Trigger**
- Initially implement manual trigger via API endpoint
- Future: Add automatic summarization after N messages (configurable)
- Rationale: Manual control allows testing and refinement before automation

**2. Memory Embedding Model**
- Use OpenAI text-embedding-3-small (1536 dimensions)
- Consistent with existing RAG system
- Rationale: Proven performance, cost-effective

**3. Working Memory Structure**
```json
{
  "context": "Task-specific context string",
  "tool_history": [
    {"tool": "browser.open", "result": "success", "timestamp": "..."}
  ],
  "intermediate_results": {
    "key": "value"
  }
}
```

**4. Memory Types**
- `fact`: Factual information about the project
- `preference`: User preferences and settings
- `decision`: Important decisions made
- `learning`: Insights from task execution

### Performance Considerations

- Vector similarity search uses cosine distance (pgvector default)
- Add ivfflat index for faster similarity queries on large datasets
- Batch embedding generation to reduce API calls
- Cache frequently accessed memories (future optimization)

### Security Considerations

- Memories are scoped to projects (no cross-project leakage)
- API endpoints require project_id validation
- Sensitive information should be filtered before storage (future enhancement)

### Future Enhancements

- Automatic memory consolidation (merge similar memories)
- Memory importance scoring and pruning
- Multi-modal memories (images, code snippets)
- Memory versioning and history
- User-editable memories via UI

