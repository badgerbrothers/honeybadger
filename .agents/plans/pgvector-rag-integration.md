# Feature: pgvector Integration and RAG System

## Feature Description

Implement a complete RAG (Retrieval-Augmented Generation) system using pgvector for semantic search over project documents. This enables the AI agent to retrieve relevant context from uploaded files (PDF, Markdown, TXT) when executing tasks, providing accurate and contextual responses based on user's project knowledge base.

The system will:
1. Set up pgvector extension in PostgreSQL for vector similarity search
2. Implement document chunking strategy for optimal retrieval
3. Generate embeddings using OpenAI's text-embedding-3-small model
4. Index document chunks with vector embeddings in the database
5. Provide similarity search API for retrieving relevant context
6. Integrate with existing document parsers and project file system

## User Story

As a Badgers platform user
I want to upload documents to my project and have the AI agent use their content when executing tasks
So that the agent can provide accurate, context-aware responses based on my specific project knowledge

## Problem Statement

Currently, the agent cannot access or understand the content of project files. Users need the ability to:
- Upload documents (PDF, Markdown, TXT) to projects
- Have documents automatically indexed for semantic search
- Retrieve relevant document sections based on task context
- Enable the agent to answer questions about uploaded documents
- Provide context-aware task execution using project knowledge

## Solution Statement

Implement a complete RAG pipeline:
1. **pgvector Setup**: Enable vector extension in PostgreSQL for efficient similarity search
2. **Document Chunking**: Split parsed documents into optimal-sized chunks (512-1024 tokens)
3. **Embedding Generation**: Use OpenAI API to generate vector embeddings for chunks
4. **Vector Storage**: Store chunks with embeddings in PostgreSQL using pgvector
5. **Similarity Search**: Implement cosine similarity search to retrieve top-k relevant chunks
6. **Integration**: Connect RAG system to agent orchestrator for context injection

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: backend (database, models, API), worker (RAG module, embeddings)
**Dependencies**: pgvector, OpenAI API (embeddings), existing document parsers

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/app/database.py` (lines 1-29) - Why: Database connection pattern, async session management
- `backend/app/config.py` (lines 1-12) - Why: Configuration pattern for adding API keys
- `worker/rag/parsers/base.py` - Why: Document parser interface already implemented
- `worker/rag/parsers/txt_parser.py` - Why: Example parser implementation
- `backend/app/models/base.py` - Why: SQLAlchemy base model pattern

### New Files to Create

- `backend/app/models/document_chunk.py` - SQLAlchemy model for document chunks with vector embeddings
- `worker/rag/embeddings.py` - Embedding generation service using OpenAI API
- `worker/rag/chunker.py` - Document chunking logic with overlap strategy
- `worker/rag/indexer.py` - Document indexing pipeline (parse → chunk → embed → store)
- `worker/rag/retriever.py` - Similarity search and context retrieval
- `backend/app/routers/rag.py` - API endpoints for document indexing and search
- `backend/alembic/versions/xxx_add_pgvector.py` - Migration to enable pgvector extension
- `backend/alembic/versions/xxx_add_document_chunks.py` - Migration for document_chunk table
- `worker/tests/test_embeddings.py` - Unit tests for embedding service
- `worker/tests/test_chunker.py` - Unit tests for chunking logic
- `worker/tests/test_indexer.py` - Unit tests for indexing pipeline
- `worker/tests/test_retriever.py` - Unit tests for retrieval

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [pgvector GitHub](https://github.com/pgvector/pgvector)
  - Specific section: Installation and Usage
  - Why: Required for setting up vector extension and understanding vector operations
- [pgvector-python](https://github.com/pgvector/pgvector-python)
  - Specific section: SQLAlchemy integration
  - Why: Shows how to use pgvector with SQLAlchemy models
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
  - Specific section: text-embedding-3-small
  - Why: Understanding embedding dimensions (1536) and API usage
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
  - Specific section: RecursiveCharacterTextSplitter
  - Why: Best practices for document chunking strategies

### Patterns to Follow

**Database Model Pattern** (from existing models):
```python
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin

class MyModel(Base, TimestampMixin):
    __tablename__ = "my_table"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
```

**Async Database Operations**:
```python
async with async_session_maker() as session:
    result = await session.execute(select(Model).where(...))
    items = result.scalars().all()
```

**Configuration Pattern**:
```python
class Settings(BaseSettings):
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
```

**Testing Pattern**:
```python
import pytest
from unittest.mock import Mock, patch

def test_function():
    """Test description."""
    # Arrange
    # Act
    # Assert
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Set up pgvector extension and database models.

**Tasks:**
- Enable pgvector extension in PostgreSQL
- Create document_chunk model with vector column
- Add OpenAI API key to configuration
- Create Alembic migrations

### Phase 2: Core RAG Components

Implement chunking, embedding, and indexing.

**Tasks:**
- Implement document chunker with overlap strategy
- Create embedding service using OpenAI API
- Build indexing pipeline (parse → chunk → embed → store)
- Add batch processing for large documents

### Phase 3: Retrieval System

Implement similarity search and context retrieval.

**Tasks:**
- Create retriever with cosine similarity search
- Implement top-k retrieval with score threshold
- Add context formatting for agent consumption
- Optimize query performance with indexes

### Phase 4: API Integration

Expose RAG functionality via API endpoints.

**Tasks:**
- Create API endpoints for document indexing
- Add search endpoint for testing
- Integrate with existing project file upload
- Add background task for async indexing

### Phase 5: Testing & Validation

Comprehensive testing of RAG pipeline.

**Tasks:**
- Unit tests for each component
- Integration tests for full pipeline
- Performance testing with large documents
- Validate retrieval quality

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: ADD pgvector dependency to backend

- **IMPLEMENT**: Add pgvector package to backend dependencies
- **PATTERN**: Follow `backend/pyproject.toml` dependency format
- **UPDATE**: Add `"pgvector>=0.2.0",` to dependencies list
- **VALIDATE**: `cd backend && uv sync && uv pip list | grep pgvector`

### Task 2: CREATE Alembic migration for pgvector extension

- **IMPLEMENT**: Enable pgvector extension in PostgreSQL
- **PATTERN**: Alembic migration with raw SQL
- **CREATE**: `backend/alembic/versions/xxx_enable_pgvector.py`
- **SQL**: `CREATE EXTENSION IF NOT EXISTS vector;`
- **VALIDATE**: `cd backend && uv run alembic upgrade head`

### Task 3: CREATE backend/app/models/document_chunk.py

- **IMPLEMENT**: SQLAlchemy model for document chunks with vector embeddings
- **PATTERN**: Mirror `backend/app/models/base.py` (TimestampMixin)
- **IMPORTS**: `from pgvector.sqlalchemy import Vector`, `from sqlalchemy import String, Integer, Text, ForeignKey`
- **FIELDS**:
  - `id: int` (primary key)
  - `project_id: str` (foreign key to projects)
  - `file_path: str` (source file path)
  - `chunk_index: int` (position in document)
  - `content: str` (chunk text content)
  - `embedding: Vector(1536)` (OpenAI embedding)
  - `token_count: int` (chunk size in tokens)
  - `metadata: JSON` (page numbers, headers, etc.)
- **GOTCHA**: Vector dimension must match embedding model (1536 for text-embedding-3-small)
- **VALIDATE**: `cd backend && uv run python -c "from app.models.document_chunk import DocumentChunk; print('OK')"`

### Task 4: CREATE Alembic migration for document_chunk table

- **IMPLEMENT**: Create document_chunk table with vector column
- **PATTERN**: Alembic auto-generate migration
- **COMMAND**: `cd backend && uv run alembic revision --autogenerate -m "add document_chunk table"`
- **VALIDATE**: `cd backend && uv run alembic upgrade head`

### Task 5: UPDATE backend/app/config.py

- **IMPLEMENT**: Add OpenAI API key and embedding configuration
- **PATTERN**: Follow existing Settings class pattern
- **ADD**:
  - `openai_api_key: str = ""`
  - `embedding_model: str = "text-embedding-3-small"`
  - `embedding_dimension: int = 1536`
  - `chunk_size: int = 512`
  - `chunk_overlap: int = 50`
- **VALIDATE**: `cd backend && uv run python -c "from app.config import settings; print(settings.embedding_model)"`

### Task 6: ADD openai dependency to worker

- **IMPLEMENT**: Add OpenAI SDK to worker dependencies
- **PATTERN**: Follow `worker/pyproject.toml` dependency format
- **UPDATE**: OpenAI already in dependencies, verify version `>=1.10.0`
- **VALIDATE**: `cd worker && uv sync && uv pip list | grep openai`

### Task 7: CREATE worker/rag/embeddings.py

- **IMPLEMENT**: Embedding generation service using OpenAI API
- **PATTERN**: Simple class with async methods
- **IMPORTS**: `from openai import AsyncOpenAI`, `from typing import List`
- **CLASS**: `EmbeddingService` with:
  - `__init__(api_key: str, model: str)`
  - `async generate_embedding(text: str) -> List[float]`
  - `async generate_embeddings_batch(texts: List[str]) -> List[List[float]]`
- **GOTCHA**: Handle rate limits with retry logic, batch size max 2048 texts
- **VALIDATE**: `cd worker && uv run python -c "from rag.embeddings import EmbeddingService; print('OK')"`

### Task 8: CREATE worker/rag/chunker.py

- **IMPLEMENT**: Document chunking with overlap strategy
- **PATTERN**: Simple function-based approach
- **IMPORTS**: `from typing import List, Dict, Any`
- **FUNCTION**: `chunk_text(text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]`
- **LOGIC**: Split by sentences/paragraphs, maintain overlap, track positions
- **RETURN**: List of dicts with `{"content": str, "chunk_index": int, "start_pos": int, "end_pos": int}`
- **GOTCHA**: Use tiktoken for accurate token counting (OpenAI tokenizer)
- **VALIDATE**: `cd worker && uv run python -c "from rag.chunker import chunk_text; print(len(chunk_text('test ' * 1000, 512, 50)))"`

### Task 9: ADD tiktoken dependency to worker

- **IMPLEMENT**: Add tiktoken for token counting
- **PATTERN**: Follow `worker/pyproject.toml` dependency format
- **UPDATE**: Add `"tiktoken>=0.5.0",` to dependencies
- **VALIDATE**: `cd worker && uv sync && uv pip list | grep tiktoken`

### Task 10: CREATE worker/rag/indexer.py

- **IMPLEMENT**: Document indexing pipeline
- **PATTERN**: Class-based service with async methods
- **IMPORTS**: Import parsers, chunker, embeddings, database session
- **CLASS**: `DocumentIndexer` with:
  - `async index_document(project_id: str, file_path: str, content: str)`
  - `async _parse_document(file_path: str, content: str) -> str`
  - `async _chunk_document(text: str) -> List[Dict]`
  - `async _generate_embeddings(chunks: List[Dict]) -> List[Dict]`
  - `async _store_chunks(project_id: str, file_path: str, chunks: List[Dict])`
- **GOTCHA**: Use batch embedding generation (max 2048 per batch), handle large documents
- **VALIDATE**: `cd worker && uv run python -c "from rag.indexer import DocumentIndexer; print('OK')"`

### Task 11: CREATE worker/rag/retriever.py

- **IMPLEMENT**: Similarity search and retrieval
- **PATTERN**: Class-based service with async methods
- **IMPORTS**: `from sqlalchemy import select, func`, `from pgvector.sqlalchemy import Vector`
- **CLASS**: `DocumentRetriever` with:
  - `async retrieve(query: str, project_id: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict]`
  - `async _generate_query_embedding(query: str) -> List[float]`
  - `async _search_similar_chunks(embedding: List[float], project_id: str, top_k: int, threshold: float)`
- **QUERY**: Use cosine similarity: `1 - (embedding <=> query_embedding)`
- **GOTCHA**: pgvector uses `<=>` operator for cosine distance (1 - similarity)
- **VALIDATE**: `cd worker && uv run python -c "from rag.retriever import DocumentRetriever; print('OK')"`

### Task 12: CREATE worker/tests/test_embeddings.py

- **IMPLEMENT**: Unit tests for embedding service
- **PATTERN**: pytest with mocking
- **TESTS**:
  - `test_generate_embedding_success()` - Mock OpenAI API response
  - `test_generate_embeddings_batch()` - Test batch processing
  - `test_embedding_dimension()` - Verify 1536 dimensions
  - `test_api_error_handling()` - Test error cases
- **VALIDATE**: `cd worker && uv run pytest tests/test_embeddings.py -v`

### Task 13: CREATE worker/tests/test_chunker.py

- **IMPLEMENT**: Unit tests for chunking logic
- **PATTERN**: pytest with fixtures
- **TESTS**:
  - `test_chunk_text_basic()` - Test basic chunking
  - `test_chunk_overlap()` - Verify overlap works correctly
  - `test_chunk_token_count()` - Validate token counting
  - `test_empty_text()` - Handle edge case
- **VALIDATE**: `cd worker && uv run pytest tests/test_chunker.py -v`

### Task 14: CREATE worker/tests/test_indexer.py

- **IMPLEMENT**: Unit tests for indexing pipeline
- **PATTERN**: pytest with mocking
- **TESTS**:
  - `test_index_document_success()` - Mock full pipeline
  - `test_parse_document()` - Test parser integration
  - `test_batch_embedding_generation()` - Test batching
  - `test_store_chunks()` - Test database storage
- **VALIDATE**: `cd worker && uv run pytest tests/test_indexer.py -v`

### Task 15: CREATE worker/tests/test_retriever.py

- **IMPLEMENT**: Unit tests for retrieval
- **PATTERN**: pytest with database fixtures
- **TESTS**:
  - `test_retrieve_success()` - Test similarity search
  - `test_top_k_filtering()` - Verify top-k works
  - `test_threshold_filtering()` - Test score threshold
  - `test_project_isolation()` - Ensure project filtering
- **VALIDATE**: `cd worker && uv run pytest tests/test_retriever.py -v`

### Task 16: CREATE backend/app/routers/rag.py

- **IMPLEMENT**: API endpoints for RAG operations
- **PATTERN**: Follow existing router patterns
- **ENDPOINTS**:
  - `POST /projects/{project_id}/documents/index` - Index a document
  - `POST /projects/{project_id}/search` - Search for similar chunks
  - `GET /projects/{project_id}/chunks` - List indexed chunks
  - `DELETE /projects/{project_id}/chunks/{chunk_id}` - Delete chunk
- **VALIDATE**: `cd backend && uv run python -c "from app.routers.rag import router; print('OK')"`

### Task 17: UPDATE backend/app/main.py

- **IMPLEMENT**: Register RAG router
- **PATTERN**: Follow existing router registration
- **ADD**: `app.include_router(rag.router, prefix="/api", tags=["rag"])`
- **VALIDATE**: `cd backend && uv run python -c "from app.main import app; print('OK')"`

### Task 18: CREATE backend/tests/test_api_rag.py

- **IMPLEMENT**: Integration tests for RAG API
- **PATTERN**: Follow existing API test patterns
- **TESTS**:
  - `test_index_document()` - Test document indexing endpoint
  - `test_search_chunks()` - Test search endpoint
  - `test_list_chunks()` - Test listing endpoint
  - `test_delete_chunk()` - Test deletion endpoint
- **VALIDATE**: `cd backend && uv run pytest tests/test_api_rag.py -v`

---

## TESTING STRATEGY

### Unit Tests

**Framework**: pytest with pytest-asyncio

**Coverage Requirements**: 80%+ for all RAG modules

**Test Structure**:
- Mock external dependencies (OpenAI API, database)
- Use fixtures for common test data
- Test happy paths and error cases
- Validate edge cases (empty documents, large documents)

### Integration Tests

**Scope**: Full RAG pipeline from document upload to retrieval

**Test Scenarios**:
1. Index PDF document and retrieve relevant chunks
2. Index multiple documents and test cross-document search
3. Test project isolation (chunks from project A not returned for project B)
4. Performance test with large documents (>100 pages)

### Edge Cases

1. **Empty Documents**: Handle documents with no extractable text
2. **Large Documents**: Test chunking and batching for 100+ page PDFs
3. **Special Characters**: Unicode, emojis in document content
4. **Duplicate Indexing**: Handle re-indexing same document
5. **Invalid Embeddings**: Handle API failures gracefully
6. **Zero Results**: Search queries with no similar chunks

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd backend && uv run ruff check app/models/document_chunk.py app/routers/rag.py
cd worker && uv run ruff check rag/embeddings.py rag/chunker.py rag/indexer.py rag/retriever.py
```

### Level 2: Unit Tests

```bash
cd worker && uv run pytest tests/test_embeddings.py tests/test_chunker.py tests/test_indexer.py tests/test_retriever.py -v
```

### Level 3: Integration Tests

```bash
cd backend && uv run pytest tests/test_api_rag.py -v
```

### Level 4: Manual Validation

```bash
# Start backend
cd backend && uv run uvicorn app.main:app --reload --port 8000 &

# Test document indexing
curl -X POST http://localhost:8000/api/projects/test-proj/documents/index \
  -H "Content-Type: application/json" \
  -d '{"file_path": "test.txt", "content": "Sample document content"}'

# Test search
curl -X POST http://localhost:8000/api/projects/test-proj/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sample", "top_k": 5}'
```

### Level 5: Database Validation

```bash
# Verify pgvector extension
psql -U badgers -d badgers -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# Check document_chunk table
psql -U badgers -d badgers -c "\d document_chunk"

# Verify vector index
psql -U badgers -d badgers -c "\di document_chunk*"
```

---

## ACCEPTANCE CRITERIA

- [ ] pgvector extension enabled in PostgreSQL
- [ ] DocumentChunk model created with vector column (1536 dimensions)
- [ ] Embedding service generates embeddings using OpenAI API
- [ ] Document chunker splits text with configurable size and overlap
- [ ] Indexing pipeline processes documents end-to-end (parse → chunk → embed → store)
- [ ] Retriever performs cosine similarity search with top-k and threshold filtering
- [ ] API endpoints for indexing and searching documents
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥80% for RAG modules
- [ ] Integration tests verify full pipeline
- [ ] Project isolation enforced (chunks filtered by project_id)
- [ ] Performance acceptable for documents up to 100 pages
- [ ] Error handling for API failures and edge cases

---

## COMPLETION CHECKLIST

- [ ] All 18 tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] Ruff linting passes with zero errors
- [ ] Manual API testing confirms functionality
- [ ] Database migrations applied successfully
- [ ] pgvector extension verified in PostgreSQL
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

**1. Chunking Strategy**
- Fixed-size chunks (512 tokens) with overlap (50 tokens)
- Maintains context across chunk boundaries
- Optimal for embedding model context window
- Simple and predictable behavior

**2. Embedding Model**
- OpenAI text-embedding-3-small (1536 dimensions)
- Good balance of quality and cost
- Fast inference time
- Well-documented and reliable

**3. Vector Storage**
- pgvector extension in PostgreSQL
- Keeps vectors with relational data
- Simpler architecture than separate vector DB
- Good performance for MVP scale (<1M vectors)

**4. Similarity Metric**
- Cosine similarity (via cosine distance)
- Standard for text embeddings
- Normalized by vector length
- Intuitive score interpretation (0-1)

**5. Retrieval Strategy**
- Top-k with score threshold
- Filters low-quality matches
- Configurable per query
- Returns ranked results

### Trade-offs

**Simplicity vs Performance**
- Chose pgvector over specialized vector DBs (Pinecone, Weaviate)
- Acceptable for MVP scale (<100K documents)
- Can migrate to specialized DB if needed
- Reduces operational complexity

**Chunking vs Semantic Splitting**
- Fixed-size chunks vs semantic boundaries (paragraphs, sections)
- Fixed-size is simpler and more predictable
- May split mid-sentence but overlap mitigates this
- Can enhance with semantic splitting later

**Batch vs Streaming**
- Batch embedding generation vs streaming
- Batch is simpler and more efficient for API
- Acceptable latency for MVP
- Can add streaming for large documents later

### Future Enhancements

1. **Hybrid Search**: Combine vector similarity with keyword search (BM25)
2. **Reranking**: Use cross-encoder model to rerank top-k results
3. **Metadata Filtering**: Filter by document type, date, author before similarity search
4. **Incremental Updates**: Update embeddings when documents change
5. **Query Expansion**: Expand user queries with synonyms/related terms
6. **Caching**: Cache embeddings for common queries
7. **Compression**: Use quantization to reduce vector storage size

### Integration Notes

**Agent Integration** (Future):
- Retriever will be called by agent orchestrator
- Retrieved chunks injected into agent context
- Agent can request more context if needed
- Track which chunks were used in task execution

**Performance Expectations**:
- Embedding generation: ~100ms per chunk (OpenAI API)
- Indexing 10-page PDF: ~5-10 seconds
- Similarity search: <100ms for 10K chunks
- Memory usage: ~6KB per chunk (1536 floats * 4 bytes)

### Security Considerations

- OpenAI API key stored in environment variables
- Project isolation enforced at database level
- No user input directly in SQL queries (use parameterized queries)
- Rate limiting on API endpoints to prevent abuse
- Validate file paths to prevent directory traversal

---

## CONFIDENCE SCORE

**7/10** - Good confidence for one-pass implementation success

**Reasoning:**
- Clear requirements and well-defined scope
- pgvector is well-documented with SQLAlchemy examples
- OpenAI embeddings API is straightforward
- Existing patterns to follow (models, routers, tests)
- Comprehensive task breakdown with validation

**Risk Factors:**
- pgvector setup may require PostgreSQL configuration
- Alembic migrations with extensions can be tricky
- OpenAI API rate limits may need handling
- Performance tuning may be needed for large documents
- Vector index optimization requires testing

**Mitigation:**
- Each task has immediate validation
- Test-driven approach catches issues early
- Can start with small documents and scale up
- Fallback to simpler approaches if needed
