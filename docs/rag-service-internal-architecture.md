# RAG Service Internal Architecture

This note documents the internal split inside `services/rag-service`.

## Current Intent

- `index_job_service.py` owns index-job creation and RabbitMQ publishing.
- `search_service.py` owns retrieval, query rewrite, reranking, and chunk management.
- `worker-indexjob` continues to own parsing, chunking, embedding generation, and chunk persistence.

## Scope

This is an internal refactor of the existing `rag-service` microservice. It does not introduce a new deployable service and does not yet remove duplicated RAG core logic between `services/rag-service/app/rag` and `worker/rag`.

## Follow-On Work

- Extract shared RAG core code into a real shared package if the team decides to consolidate `rag-service` and `worker` retrieval/indexing helpers.
- Decide whether task-run retrieval should keep querying directly in worker or move behind a shared retrieval layer.
