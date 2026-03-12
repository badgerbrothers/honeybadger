# Code Review: File Upload Feature (Plan 3.3)

## Stats

- Files Modified: 4
- Files Added: 5
- Files Deleted: 0
- New lines: +596
- Deleted lines: -4

## Summary

Reviewed file upload feature implementation including backend API endpoints, frontend components, and tests. Found 8 issues: 2 high severity, 3 medium severity, 3 low severity.

---

## Issues Found

### HIGH SEVERITY


#### Issue 1: Transaction Management - Storage Upload Before Database Write

**severity**: high
**file**: backend/app/routers/projects.py
**line**: 91-107
**issue**: Storage upload happens before database transaction, risking orphaned files
**detail**: The code uploads to MinIO (line 91-95) before writing to database (line 105-107). If storage succeeds but database fails, orphaned files remain in MinIO with no database record. This creates data inconsistency and wasted storage.
**suggestion**: Reverse the order - write database record first with a pending status, then upload to storage, then update status to complete. Or wrap in try-catch with rollback logic to delete from storage if database fails.

```python
# Better approach:
try:
    # Create DB record first
    node = ProjectNode(...)
    db.add(node)
    await db.flush()  # Get ID without committing
    
    # Then upload to storage
    await storage_service.upload_file(...)
    
    # Finally commit
    await db.commit()
except Exception as e:
    await db.rollback()
    # Clean up storage if needed
    raise
```

#### Issue 2: Missing Storage Service Mocks in Tests

**severity**: high
**file**: backend/tests/test_api_projects.py
**line**: 26-119
**issue**: Tests call real storage_service without mocking, causing test failures
**detail**: All file upload tests (lines 26-119) make actual calls to storage_service.upload_file() and storage_service.delete_file() without mocking. This requires a real MinIO instance to be running, causing tests to fail in CI/CD and local environments. Tests should be isolated and not depend on external services.
**suggestion**: Add pytest fixtures to mock storage_service in conftest.py:

```python
@pytest.fixture(autouse=True)
def mock_storage_service(monkeypatch):
    async def mock_upload(*args, **kwargs):
        return None
    async def mock_delete(*args, **kwargs):
        return None
    monkeypatch.setattr("app.services.storage.storage_service.upload_file", mock_upload)
    monkeypatch.setattr("app.services.storage.storage_service.delete_file", mock_delete)
```

### MEDIUM SEVERITY

#### Issue 3: File Deletion Order Risk

**severity**: medium
**file**: backend/app/routers/projects.py
**line**: 148-152
**issue**: Storage deleted before database record, risking data inconsistency
**detail**: Code deletes from storage (line 149) before deleting database record (line 151-152). If storage deletion succeeds but database deletion fails, the database will reference a non-existent file. Users will see the file listed but cannot access it.
**suggestion**: Reverse the order - delete database record first, then delete from storage. Storage cleanup can be done asynchronously if needed.

```python
# Better approach:
await db.delete(node)
await db.commit()
# Then delete from storage (even if this fails, DB is consistent)
try:
    await storage_service.delete_file(storage_path)
except Exception as e:
    logger.warning(f"Failed to delete file from storage: {e}")
```

#### Issue 4: File Extension Validation Edge Case

**severity**: medium
**file**: frontend/src/features/projects/components/FileUploadZone.tsx
**line**: 25
**issue**: File extension extraction doesn't handle edge cases properly
**detail**: `const ext = '.' + file.name.split('.').pop()?.toLowerCase();` doesn't handle files without extensions (e.g., "README") or files starting with dot (e.g., ".gitignore"). For "README", it returns ".readme" instead of empty string. For ".gitignore", it returns ".gitignore" which is correct but coincidental.
**suggestion**: Use more robust extension extraction:

```typescript
const getFileExtension = (filename: string): string => {
  const lastDot = filename.lastIndexOf('.');
  if (lastDot === -1 || lastDot === 0) return '';
  return filename.slice(lastDot).toLowerCase();
};
const ext = getFileExtension(file.name);
```

#### Issue 5: Missing Error Handling for Storage Operations

**severity**: medium
**file**: backend/app/routers/projects.py
**line**: 91-95, 149
**issue**: No try-catch around storage_service calls
**detail**: Calls to storage_service.upload_file() and storage_service.delete_file() have no error handling. If MinIO is unavailable or network fails, generic exceptions propagate to users without context. Should provide better error messages.
**suggestion**: Add try-catch with specific error messages:

```python
try:
    await storage_service.upload_file(...)
except Exception as e:
    logger.error(f"Storage upload failed: {e}")
    raise HTTPException(status_code=503, detail="File storage service unavailable")
```

### LOW SEVERITY

#### Issue 6: Inconsistent API Client Usage

**severity**: low
**file**: frontend/src/features/projects/api/files.ts
**line**: 20-26
**issue**: uploadProjectFile uses fetch() while other functions use request()
**detail**: The uploadProjectFile function uses native fetch() (lines 20-26) while fetchProjectFiles and deleteProjectFile use the request() utility (lines 36-43). This inconsistency makes the codebase harder to maintain and may bypass centralized error handling or auth logic in request().
**suggestion**: Refactor request() utility to support FormData, or document why fetch() is necessary here. If request() doesn't support FormData, add that capability:

```typescript
// In lib/api.ts
export async function request<T>(url: string, options?: RequestInit & { formData?: FormData }): Promise<T> {
  const { formData, ...fetchOptions } = options || {};
  if (formData) {
    fetchOptions.body = formData;
  }
  // ... rest of request logic
}
```

#### Issue 7: Weak Error Message Extraction

**severity**: low
**file**: frontend/src/features/projects/api/files.ts
**line**: 29
**issue**: Error detail extraction assumes specific error format
**detail**: `error.detail` assumes backend returns `{detail: string}` format. If backend returns different error format or plain text, this fails silently and shows undefined.
**suggestion**: Add fallback chain:

```typescript
const error = await response.json().catch(() => ({ detail: response.statusText }));
throw new Error(error.detail || error.message || 'Upload failed');
```

#### Issue 8: No Delete Confirmation Dialog

**severity**: low
**file**: frontend/src/features/projects/components/FileList.tsx
**line**: 58
**issue**: Delete button has no confirmation, risking accidental deletion
**detail**: Clicking delete immediately removes the file without confirmation. Users may accidentally click delete and lose data permanently.
**suggestion**: Add confirmation dialog:

```typescript
<Button
  onClick={() => {
    if (confirm(`Delete ${file.name}?`)) {
      deleteFile(file.id);
    }
  }}
  className="text-red-600 hover:text-red-700"
>
  Delete
</Button>
```

---

## Recommendations

1. **Priority 1**: Fix Issue #1 (transaction management) and Issue #2 (mock storage in tests)
2. **Priority 2**: Fix Issue #3 (deletion order) and Issue #5 (error handling)
3. **Priority 3**: Address remaining low-severity issues for better UX

## Overall Assessment

The file upload feature is functionally complete with proper validation, type safety, and UI components. However, critical issues with transaction management and test infrastructure must be fixed before production deployment. The code follows project patterns well but needs better error handling and edge case coverage.
