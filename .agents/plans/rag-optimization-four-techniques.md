# Feature: RAG System Optimization (Post-Microservices)

## Scope
This plan is updated for the **post-split architecture** where RAG API runs in `services/rag-service` and index execution runs in shared worker (`worker/worker_indexjob.py` + `worker/rag/*`).

## Goals
Implement 4 optimizations in the current microservice topology:
1. Hybrid retrieval (vector + PostgreSQL full-text)
2. Reranking (Cross-Encoder with graceful fallback)
3. Semantic chunking (sentence-aware chunk boundaries)
4. Query rewriting (optional LLM rewrite with cache + fallback)

## Current Architecture Baseline
- RAG API: `services/rag-service/app/routers/rag.py`
- RAG orchestration: `services/rag-service/app/services/rag_service.py`
- RAG data model: `services/rag-service/app/models/document_chunk.py`
- Index worker entry: `worker/worker_indexjob.py`
- Index pipeline: `worker/rag/indexer.py`
- Compose routing: `nginx/nginx.conf` -> `/api/rag` -> `rag-service`

## Step-by-Step Tasks

### Phase 1: Hybrid Search
1. Update `services/rag-service/app/models/document_chunk.py`
- Add `text_search_vector` (`TSVECTOR`) and GIN index metadata.

2. Update `services/rag-service/app/database.py`
- Ensure `vector` extension exists.
- Add idempotent schema patching for existing DBs:
  - `ALTER TABLE document_chunk ADD COLUMN IF NOT EXISTS text_search_vector TSVECTOR`
  - `CREATE INDEX IF NOT EXISTS ix_document_chunk_text_search_vector ... USING gin`

3. Create `services/rag-service/app/rag/hybrid_retriever.py`
- Implement vector retrieval.
- Implement full-text retrieval with `websearch_to_tsquery`.
- Implement RRF fusion.

### Phase 2: Reranking
4. Update `services/rag-service/pyproject.toml`
- Add `sentence-transformers>=2.2.0`.

5. Create `services/rag-service/app/rag/reranker.py`
- Lazy-load CrossEncoder (`BAAI/bge-reranker-base`).
- If model load/inference fails, degrade to original ranking.

### Phase 3: Semantic Chunking
6. Update `services/rag-service/pyproject.toml`
- Add `nltk>=3.8.0`.

7. Create `services/rag-service/app/rag/semantic_chunker.py`
- Sentence-aware chunking with token cap fallback.

8. Update `worker/pyproject.toml`
- Add `nltk>=3.8.0` for worker-side indexing runtime.

9. Create `worker/rag/semantic_chunker.py`
- Same sentence-aware chunking strategy for real index job path.

10. Update `worker/rag/indexer.py`
- Switch chunking to semantic mode by default (fallback available).
- After storing chunks, update `text_search_vector` via SQL for indexed file.

### Phase 4: Query Rewriting + Pipeline Integration
11. Create `services/rag-service/app/rag/query_rewriter.py`
- Optional LLM rewrite (`expand`/`clarify`) with in-memory TTL cache.
- Failures return original query.

12. Update `services/rag-service/app/services/rag_service.py`
- Integrate full pipeline:
  - optional rewrite
  - hybrid retrieval (or vector-only fallback)
  - optional reranking
  - threshold filtering + top_k

13. Update `services/rag-service/app/routers/rag.py`
- Add query flags:
  - `use_hybrid`
  - `use_reranker`
  - `use_query_rewrite`

## Tests to Add
- `services/rag-service/tests/test_hybrid_retriever.py`
- `services/rag-service/tests/test_reranker.py`
- `services/rag-service/tests/test_semantic_chunker.py`
- `services/rag-service/tests/test_query_rewriter.py`

## Validation Commands

### Level 1: Static checks
```bash
cd services/rag-service && uv run ruff check app/ tests/
cd worker && uv run ruff check rag/indexer.py rag/semantic_chunker.py
```

### Level 2: Unit tests
```bash
cd services/rag-service && uv run pytest tests/test_hybrid_retriever.py -v
cd services/rag-service && uv run pytest tests/test_reranker.py -v
cd services/rag-service && uv run pytest tests/test_semantic_chunker.py -v
cd services/rag-service && uv run pytest tests/test_query_rewriter.py -v
```

### Level 3: Import/runtime sanity
```bash
cd services/rag-service && uv run python -c "from app.rag.hybrid_retriever import HybridRetriever; from app.rag.reranker import RerankerService; from app.rag.semantic_chunker import SemanticChunker; from app.rag.query_rewriter import QueryRewriter; print('OK')"
cd worker && uv run python -c "from rag.semantic_chunker import SemanticChunker; from rag.indexer import DocumentIndexer; print('OK')"
```

### Level 4: Service-level smoke (Docker optional)
If Docker runtime/display is unavailable, this level may be skipped and recorded as deferred.

## Acceptance Criteria
- RAG model supports `text_search_vector` and DB has corresponding GIN index.
- Search endpoint supports 3 optimization flags.
- RAG service pipeline supports rewrite + hybrid + rerank with graceful degradation.
- Worker indexing uses semantic chunking and writes `text_search_vector`.
- New unit tests pass.
- Existing behavior remains backward compatible when flags are disabled.
