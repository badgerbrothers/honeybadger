# RAG Upload Follow-Ups

## Storage-Service Parity

`services/rag-service` upload endpoints now avoid eager full-file buffering before MinIO upload.

`services/storage-service/app/main.py` still uses the older eager-buffering path:

- `await file.read()`
- `BytesIO(data)` passed to `put_object(...)`

This is acceptable for now because the current RAG and project upload flows call MinIO directly through `services/rag-service/app/services/storage.py`.

If product traffic later shifts toward the storage proxy upload route, align `storage-service` with the same streaming upload pattern used in `rag-service`.
