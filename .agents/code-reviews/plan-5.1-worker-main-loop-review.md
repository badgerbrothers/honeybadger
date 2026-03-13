# Code Review: Worker Main Loop Implementation (Plan 5.1)

**Date:** 2026-03-14
**Reviewer:** Claude
**Scope:** Worker main loop implementation and related changes

## Stats

- Files Modified: 6
- Files Added: 4
- Files Deleted: 0
- New lines: ~400
- Deleted lines: ~3

## Summary

The worker main loop implementation is functionally complete and well-structured. However, several issues need to be addressed before production deployment, including deprecated API usage, a string parsing bug, and missing error handling.

## Issues Found

### CRITICAL

None

### HIGH

**Issue 1: String Parsing Bug**

```
severity: high
file: worker/main.py
line: 123
issue: Incorrect string suffix removal using rstrip()
detail: rstrip('mg') removes any 'm' or 'g' characters from the end, not the suffix 'mg'.
        For "512mg" it works, but "512gm" also becomes "512", and "512mmm" becomes "512".
        This will cause incorrect memory limit values to be passed to Docker.
suggestion: Use removesuffix() method (Python 3.9+):
            memory_limit=int(settings.sandbox_memory_limit.removesuffix('m').removesuffix('g'))
            Or parse properly:
            mem_str = settings.sandbox_memory_limit.lower()
            if mem_str.endswith('mb'):
                memory_limit = int(mem_str[:-2])
            elif mem_str.endswith('m'):
                memory_limit = int(mem_str[:-1])
```

**Issue 2: Deprecated datetime.utcnow() Usage**

```
severity: high
file: worker/main.py
lines: 77, 163, 170, 179
issue: Using deprecated datetime.utcnow() method
detail: datetime.utcnow() is deprecated in Python 3.12+ and will be removed in future versions.
        The deprecation warning is already showing in test output.
suggestion: Replace all instances with:
            from datetime import datetime, timezone
            datetime.now(timezone.utc)
```

### MEDIUM

**Issue 3: Missing Error Handling in File Parsers**

```
severity: medium
file: backend/rag/parsers/__init__.py
lines: 10, 18
issue: No error handling for file read operations
detail: file_path.read_text() can raise FileNotFoundError, PermissionError, or UnicodeDecodeError.
        These exceptions will propagate uncaught and may crash the indexing process.
suggestion: Add try-except blocks:
            try:
                text = file_path.read_text(encoding="utf-8")
                return {"text": text, "metadata": {}}
            except FileNotFoundError:
                raise ValueError(f"File not found: {file_path}")
            except UnicodeDecodeError as e:
                raise ValueError(f"Failed to decode file {file_path}: {e}")
```

**Issue 4: Generic Exception Handling Loses Context**

```
severity: medium
file: backend/rag/parsers/__init__.py
line: 31-32
issue: Catching generic Exception and re-raising as ValueError loses original exception type
detail: The original exception type and full stack trace are lost, making debugging harder.
suggestion: Use exception chaining:
            except Exception as e:
                raise ValueError(f"Failed to parse PDF: {e}") from e
```

**Issue 5: Fragile locals() Check**

```
severity: medium
file: worker/main.py
line: 177
issue: Using 'task_run' in locals() is fragile and not Pythonic
detail: This pattern is error-prone and makes the code harder to understand.
        If variable naming changes, this check silently breaks.
suggestion: Use a flag or restructure:
            task_run = None
            try:
                result = await session.execute(...)
                task_run = result.scalar_one()
                # ... rest of code
            except Exception as e:
                if task_run is not None:
                    task_run.status = TaskStatus.FAILED
                    # ...
```

### LOW

**Issue 6: Hardcoded Database Credentials in Default**

```
severity: low
file: worker/config.py
line: 9
issue: Database URL with credentials in default value
detail: While this is for development, hardcoded credentials in code are a security risk
        if accidentally committed without proper .env override in production.
suggestion: Consider using empty string as default and requiring .env configuration:
            database_url: str = ""
            Or add a validation check in __init__ to ensure it's overridden in production.
```

**Issue 7: Session Reuse Across Function Boundary**

```
severity: low
file: worker/main.py
line: 203
issue: Same session used to claim task and execute it
detail: The session that claimed the task is passed to execute_task_run().
        If execute_task_run() fails and rolls back, the session state may be inconsistent.
suggestion: Consider using separate sessions or ensure proper transaction boundaries:
            async with async_session_maker() as claim_session:
                task_run = await get_next_pending_task(claim_session)
            if task_run:
                async with async_session_maker() as exec_session:
                    await execute_task_run(task_run.id, exec_session)
```

## Positive Observations

1. ✅ Excellent test coverage with proper mocking
2. ✅ Good use of structured logging with context binding
3. ✅ Proper async/await patterns throughout
4. ✅ Graceful shutdown handling with signals
5. ✅ Clean separation of concerns (polling, claiming, executing)
6. ✅ Comprehensive error handling and cleanup in execute_task_run()
7. ✅ Type hints used appropriately

## Recommendations

### Must Fix Before Production

1. Fix the rstrip() bug (Issue 1) - this will cause runtime errors
2. Replace deprecated datetime.utcnow() (Issue 2) - will break in future Python versions

### Should Fix Soon

3. Add error handling to file parsers (Issue 3)
4. Use exception chaining in PDF parser (Issue 4)
5. Replace locals() check with cleaner pattern (Issue 5)

### Consider for Future

6. Review database credential handling (Issue 6)
7. Evaluate session management strategy (Issue 7)

## Overall Assessment

**Status:** PASS with required fixes

The implementation is solid and follows good practices. The identified issues are fixable and don't represent fundamental design flaws. Once the HIGH severity issues are addressed, this code is ready for production deployment.

**Code Quality:** 8/10
**Test Coverage:** 9/10
**Security:** 7/10 (due to hardcoded credentials)
**Maintainability:** 8/10
