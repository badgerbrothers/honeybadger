# Code Review: Web Fetch Tool

**Date**: 2026-03-12
**Reviewer**: Claude (Automated Review)
**Scope**: Web Fetch tool implementation

---

## Stats

- Files Modified: 2
- Files Added: 2
- Files Deleted: 0
- New lines: ~140
- Deleted lines: 0

---

## Issues Found

### Issue 1

**severity**: medium
**file**: worker/tools/web.py
**line**: 39-41
**issue**: No SSRF (Server-Side Request Forgery) protection
**detail**: The tool accepts any URL without validation. An attacker could use this to access internal services (localhost, 127.0.0.1, 169.254.169.254 for cloud metadata, private IP ranges like 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16). While the tool runs in a sandboxed Docker container, defense in depth is important.
**suggestion**: Add URL validation to block private IP ranges:
```python
from urllib.parse import urlparse
import ipaddress

def _is_safe_url(url: str) -> bool:
    """Check if URL is safe (not targeting internal services)."""
    try:
        parsed = urlparse(url)
        if parsed.hostname in ['localhost', '127.0.0.1', '::1']:
            return False

        # Check for private IP ranges
        ip = ipaddress.ip_address(parsed.hostname)
        return not ip.is_private
    except (ValueError, AttributeError):
        return True  # Allow domain names

# In execute():
if not _is_safe_url(url):
    raise WebFetchError("URL targets internal/private network")
```

---

### Issue 2

**severity**: low
**file**: worker/tools/web.py
**line**: 89
**issue**: Overly broad exception handling
**detail**: The code catches all exceptions with `except Exception as e:`, which could hide bugs and make debugging difficult. For example, if there's a programming error in the code, it would be caught and wrapped as WebFetchError.
**suggestion**: Catch specific httpx exceptions:
```python
except httpx.TimeoutException as e:
    raise WebFetchTimeoutError(f"Request timed out after {timeout}s: {e}") from e
except (httpx.HTTPError, httpx.RequestError) as e:
    raise WebFetchError(f"Failed to fetch URL: {e}") from e
```

---

### Issue 3

**severity**: low
**file**: worker/tools/web.py
**line**: 51, 58
**issue**: Type hint mismatch for headers parameter
**detail**: The `fetch()` method expects `headers: Dict[str, str]`, but `params.get("headers", {})` returns `Dict[str, Any]` since params is typed as `Dict[str, Any]`. This could cause type checking issues if headers contain non-string values.
**suggestion**: Add runtime validation or adjust type hints:
```python
headers = params.get("headers", {})
if headers and not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
    raise WebFetchError("Headers must be string key-value pairs")
```
Or change the type hint to `Dict[str, Any]` and let httpx handle validation.

---

### Issue 4

**severity**: low
**file**: worker/tools/web.py
**line**: 76
**issue**: Bare except catches all exceptions including system exceptions
**detail**: Using `except Exception:` is acceptable here since we want to gracefully handle any JSON parsing failure, but it could catch KeyboardInterrupt or SystemExit in theory (though unlikely in this context).
**suggestion**: Be more specific:
```python
try:
    json_data = response.json()
except (ValueError, TypeError, AttributeError):
    pass
```

---

## Positive Observations

✅ **Clean structure**: Follows BaseTool pattern consistently
✅ **Good error handling**: Proper exception hierarchy with WebFetchError and WebFetchTimeoutError
✅ **Type hints**: All methods have proper type annotations
✅ **Logging**: Uses structlog consistently via BaseTool
✅ **Documentation**: Clear docstrings with parameter descriptions
✅ **Testing**: Comprehensive unit tests with 100% pass rate (8/8)
✅ **Async context manager**: Properly uses `async with` for httpx.AsyncClient
✅ **Timeout validation**: Validates timeout range (1-300 seconds)
✅ **Method validation**: Only allows GET and POST methods
✅ **JSON parsing**: Gracefully handles non-JSON responses
✅ **Minimal implementation**: 91 lines, no unnecessary complexity

---

## Summary

**Overall Assessment**: GOOD with minor security concern

The Web Fetch tool is well-implemented and follows project patterns. The main concerns are:
1. SSRF vulnerability (medium severity) - should be addressed before production
2. Overly broad exception handling (low severity)
3. Type hint mismatch for headers (low severity)
4. JSON parsing exception handling could be more specific (low severity)

**Recommendation**: Address Issue #1 (SSRF) before production use if the tool will be exposed to untrusted input. Issues #2-#4 are nice-to-have improvements.

**Test Status**: All 8 unit tests passing, well-structured with proper mocking. No test failures related to this module.
