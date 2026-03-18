# RAG Microservices Stability Code Review (2026-03-18)

## Findings

severity: medium  
file: worker/main.py  
line: 266  
issue: Local embedding fallback is bypassed when `OPENAI_API_KEY` is empty  
detail: `execute_document_index_job()` still hard-fails with `RuntimeError("OPENAI_API_KEY not configured for RAG indexing")` before `EmbeddingService` is instantiated. This means the new deterministic fallback path is only effective for "key exists but remote call fails", not for "key missing".  
suggestion: If the intended behavior is "indexing remains available without OpenAI", remove the hard-fail guard and rely on `EmbeddingService` fallback; otherwise document this as an explicit deployment requirement.

severity: low  
file: nginx/nginx.conf  
line: 69  
issue: First-time reranker warm-up can still exceed fixed gateway timeout in slow networks  
detail: `proxy_read_timeout` was increased to 180s and fixes common cases, but first-time HuggingFace model download remains environment-dependent. Very slow links may still hit timeout and return 504 during cold start.  
suggestion: Optionally prewarm reranker model at service startup, or make timeout configurable via env to match deployment bandwidth.

## Scope Reviewed

- services/project-service/app/database.py
- services/task-service/app/database.py
- services/rag-service/app/database.py
- services/project-service/app/services/queue_service.py
- services/task-service/app/services/queue_service.py
- worker/rag/embeddings.py
- services/rag-service/app/rag/embeddings.py
- worker/main.py
- services/rag-service/app/services/rag_service.py
- nginx/nginx.conf

## Verification Notes

- Docker startup race fixes validated: `project-service` and `task-service` both healthy after rebuild.
- DB transaction-abort fix validated: no cascading `current transaction is aborted` during startup.
- Upload -> queue -> worker indexing -> chunk persistence validated for new project/file.
- RAG search validated with:
  - default options (`use_hybrid=true,use_reranker=true,use_query_rewrite=false`)
  - baseline options (`use_hybrid=false,use_reranker=false,use_query_rewrite=false`)
  - rewrite enabled (`use_query_rewrite=true`)
- First reranker request is cold-start slow, subsequent requests are fast (warm cache behavior observed).
