# Code Review: Artifact Management & Run API Implementation

**Date**: 2026-03-13
**Reviewer**: Claude
**Scope**: Artifact management, Run API, Event streaming

## Stats

- Files Modified: 8
- Files Added: 9
- New lines: ~500
- Deleted lines: ~19

---

## Issues Found

### CRITICAL Issues

None detected.

### HIGH Severity Issues

#### Issue 1: Memory Risk with Large File Uploads
**severity**: high
**file**: backend/app/routers/artifacts.py
**line**: 37
**issue**: Entire file loaded into memory during upload
**detail**: `content = await file.read()` loads the complete file into memory. For large files (e.g., 1GB+), this can cause memory exhaustion and application crashes.
**suggestion**: Implement streaming upload or add file size limits:
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
content = await file.read(MAX_FILE_SIZE + 1)
if len(content) > MAX_FILE_SIZE:
    raise HTTPException(413, "File too large")
```

#### Issue 2: Data Inconsistency Risk in Delete Operation
**severity**: high
**file**: backend/app/routers/artifacts.py
**line**: 80-82
**issue**: Storage deleted before database record
**detail**: If database deletion fails after storage deletion, the artifact record remains but the file is gone, causing 404 errors on download.
**suggestion**: Reverse the order or use transaction-like pattern:
```python
await db.delete(artifact)
await db.commit()
await storage_service.delete_file(artifact.storage_path)
```

### MEDIUM Severity Issues

#### Issue 3: Deprecated datetime.utcnow()
**severity**: medium
**file**: backend/app/routers/runs.py
**line**: 33
**issue**: Using deprecated datetime.utcnow()
**detail**: Python 3.12+ deprecates datetime.utcnow() in favor of timezone-aware datetime.now(UTC).
**suggestion**: Replace with:
```python
from datetime import datetime, UTC
run.completed_at = datetime.now(UTC)
```

#### Issue 4: Header Injection Risk
**severity**: medium
**file**: backend/app/routers/artifacts.py
**line**: 68
**issue**: Unsanitized filename in Content-Disposition header
**detail**: Filename from database directly inserted into HTTP header without escaping. Malicious filenames with newlines could inject headers.
**suggestion**: Sanitize or quote the filename:
```python
from urllib.parse import quote
headers={"Content-Disposition": f'attachment; filename="{quote(artifact.name)}"'}
```

#### Issue 5: Async/Sync Mismatch
**severity**: medium
**file**: backend/app/services/storage.py
**line**: 34-67
**issue**: Async methods calling synchronous MinIO client
**detail**: Methods are declared async but call synchronous minio.client methods, blocking the event loop.
**suggestion**: Either remove async or use asyncio.to_thread():
```python
async def upload_file(self, ...):
    self._ensure_bucket()
    await asyncio.to_thread(
        self.client.put_object, ...
    )
```

#### Issue 6: Broad Exception Catching
**severity**: medium
**file**: backend/app/services/event_broadcaster.py
**line**: 36
**issue**: Catching generic Exception
**detail**: Catches all exceptions including system errors, making debugging difficult.
**suggestion**: Catch specific WebSocket exceptions:
```python
except (WebSocketDisconnect, RuntimeError) as e:
    logger.error("websocket_send_failed", error=str(e))
```

### LOW Severity Issues

#### Issue 7: Missing Authentication/Authorization
**severity**: low
**file**: backend/app/routers/artifacts.py, backend/app/routers/runs.py
**line**: All endpoints
**issue**: No authentication or authorization checks
**detail**: All endpoints are publicly accessible. While this may be intentional for MVP, it should be documented.
**suggestion**: Add comment indicating this is MVP scope:
```python
# TODO: Add authentication when implementing auth system
```

#### Issue 8: No File Type Validation
**severity**: low
**file**: backend/app/routers/artifacts.py
**line**: 27-32
**issue**: No validation of uploaded file types
**detail**: Any file type can be uploaded, potentially including executables or malicious files.
**suggestion**: Add MIME type whitelist if needed for production.

#### Issue 9: No Connection Limits
**severity**: low
**file**: backend/app/services/event_broadcaster.py
**line**: 15-20
**issue**: Unlimited WebSocket connections per run
**detail**: No limit on concurrent connections, could be abused for DoS.
**suggestion**: Add connection limit per run_id:
```python
MAX_CONNECTIONS_PER_RUN = 10
if len(self.connections.get(run_id, set())) >= MAX_CONNECTIONS_PER_RUN:
    raise HTTPException(429, "Too many connections")
```

#### Issue 10: Broad Exception Catching in Bucket Check
**severity**: low
**file**: backend/app/services/storage.py
**line**: 31
**issue**: Catching all exceptions in _ensure_bucket
**detail**: Silently catches all errors including network issues, making debugging difficult.
**suggestion**: Catch specific S3Error and log appropriately.

---

## Positive Observations

1. ✅ **Clean code structure**: Well-organized with clear separation of concerns
2. ✅ **Type hints**: Proper use of type annotations throughout
3. ✅ **Logging**: Structured logging with structlog
4. ✅ **Error handling**: HTTPException with appropriate status codes
5. ✅ **Lazy initialization**: StorageService uses lazy bucket checking
6. ✅ **Enum usage**: Proper use of ArtifactType enum
7. ✅ **Test coverage**: Comprehensive test suite with 30/30 tests passing

---

## Recommendations

### Immediate Actions (Before Production)
1. Fix Issue #2 (delete order) - data integrity risk
2. Fix Issue #3 (deprecated datetime) - already has deprecation warning
3. Add file size limits (Issue #1)

### Before Production Deployment
4. Implement authentication/authorization
5. Add file type validation
6. Fix async/sync mismatch in storage service
7. Sanitize filenames in headers

### Future Improvements
8. Add connection limits for WebSockets
9. Implement retry logic for MinIO operations
10. Add request rate limiting

---

## Summary

**Overall Assessment**: Good quality code with solid architecture. The implementation follows project patterns and includes comprehensive tests. Main concerns are around production readiness (file size limits, auth) and a data consistency risk in the delete operation.

**Recommendation**: ✅ **Approve with minor fixes**

The code is suitable for MVP deployment after addressing Issues #2 and #3. Other issues can be addressed in subsequent iterations.
