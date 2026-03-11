# Code Review: Browser Tools Implementation

**Date**: 2026-03-12
**Reviewer**: Claude (Automated Review)
**Scope**: Browser tools implementation (worker/tools/browser.py and related files)

---

## Stats

- Files Modified: 5
- Files Added: 4
- Files Deleted: 0
- New lines: ~500
- Deleted lines: ~3

---

## Issues Found

### Issue 1

**severity**: high
**file**: worker/tools/browser.py
**line**: 208-213
**issue**: Potential None reference error in extract() method
**detail**: After `query_selector()` returns None (if element not found despite wait_for_selector), the code attempts to call `inner_html()` or `inner_text()` on None, which will raise AttributeError. The wait_for_selector with state="attached" may pass even if element becomes detached immediately after.
**suggestion**: Add explicit None check after query_selector:
```python
element = await self.page.query_selector(selector)
if not element:
    raise BrowserSelectorError(f"Element not found: {selector}")
if format_type == "html":
    content = await element.inner_html()
else:
    content = await element.inner_text()
```

---

### Issue 2

**severity**: medium
**file**: worker/tools/browser.py
**line**: 42-68
**issue**: Missing page initialization check in execute() method
**detail**: If execute() is called without using the context manager (async with), self.page will be None, causing AttributeError when any operation tries to use it. The class allows instantiation without __aenter__, making this a real risk.
**suggestion**: Add initialization check at start of execute():
```python
async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
    if not self.page:
        raise BrowserToolError("Browser not initialized. Use 'async with BrowserTool()' context manager.")
    self._log_execution(params)
    # ... rest of method
```

---

### Issue 3

**severity**: medium
**file**: worker/tools/base.py
**line**: 28-30
**issue**: Logging may expose sensitive information
**detail**: The _log_execution method logs all parameters without sanitization. If params contain sensitive data (passwords, API keys, tokens), they will be logged in plaintext.
**suggestion**: Implement parameter sanitization before logging:
```python
def _log_execution(self, params: Dict[str, Any]):
    """Log tool execution."""
    safe_params = self._sanitize_params(params)
    self.logger.info("tool_execution_started", params=safe_params)

def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive keys from params."""
    sensitive_keys = {'password', 'token', 'api_key', 'secret'}
    return {k: '***' if k.lower() in sensitive_keys else v
            for k, v in params.items()}
```

---

### Issue 4

**severity**: low
**file**: docker/sandbox-base/Dockerfile
**line**: 45-46
**issue**: Playwright installed as root but used by sandbox user
**detail**: Playwright and Chromium are installed before switching to the sandbox user. The sandbox user may not have proper permissions to access Playwright's browser binaries in /root/.cache/ms-playwright/.
**suggestion**: Install Playwright after switching to sandbox user, or set PLAYWRIGHT_BROWSERS_PATH to a location accessible by sandbox user:
```dockerfile
# Before USER sandbox
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# After installing playwright
RUN playwright install chromium
RUN chown -R sandbox:sandbox /opt/playwright

USER sandbox
```

---

### Issue 5

**severity**: low
**file**: worker/tools/browser.py
**line**: 91
**issue**: wait_for parameter not validated
**detail**: The wait_for parameter accepts any string value but Playwright only supports specific values: "load", "domcontentloaded", "networkidle", "commit". Invalid values will cause runtime errors.
**suggestion**: Validate wait_for parameter:
```python
wait_for = params.get("wait_for", "load")
valid_wait_states = {"load", "domcontentloaded", "networkidle", "commit"}
if wait_for not in valid_wait_states:
    raise BrowserToolError(f"Invalid wait_for value: {wait_for}. Must be one of {valid_wait_states}")
```

---

## Positive Observations

✅ **Good error handling**: Proper exception hierarchy with specific error types
✅ **Clean async patterns**: Correct use of async/await and context managers
✅ **Comprehensive docstrings**: All methods well-documented with parameter descriptions
✅ **Timeout protection**: All operations have reasonable timeout values
✅ **Resource cleanup**: __aexit__ properly closes all browser resources
✅ **Type hints**: Good use of type annotations for better code clarity
✅ **Test coverage**: 5 comprehensive unit tests with proper mocking

---

## Summary

**Overall Assessment**: GOOD with minor issues

The browser tools implementation is well-structured and follows good async patterns. The main concerns are:
1. One high-severity bug (None reference in extract method)
2. Missing initialization checks
3. Potential security issue with logging sensitive data
4. Docker permission issue that may cause runtime failures

**Recommendation**: Fix Issue #1 (high severity) before deployment. Issues #2-#5 should be addressed in the next iteration.

**Test Status**: All 5 unit tests passing, but they use mocks and won't catch the None reference bug.
