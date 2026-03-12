# Feature: Web Fetch Tool

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a web.fetch tool that enables the AI agent to make HTTP requests to external APIs and websites. The tool supports GET and POST methods, handles JSON response parsing, and provides structured error handling for network operations.

## User Story

As an AI agent
I want to fetch data from external web APIs and websites
So that I can gather information, interact with web services, and complete tasks that require external data

## Problem Statement

The agent currently lacks the ability to make HTTP requests to external services. This limits its capability to:
- Fetch data from REST APIs
- Retrieve web content for analysis
- Interact with third-party services
- Gather real-time information from the internet

## Solution Statement

Implement a WebFetchTool using the httpx library (already in dependencies) that provides async HTTP request capabilities with proper timeout handling, error management, and JSON parsing. The tool will follow the established BaseTool pattern and integrate seamlessly with the existing tool ecosystem.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low
**Primary Systems Affected**: worker/tools
**Dependencies**: httpx (already in pyproject.toml)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/tools/base.py` (lines 1-39) - Why: BaseTool pattern that all tools must follow
- `worker/tools/python.py` (lines 1-82) - Why: Reference implementation showing tool structure, error handling, and logging
- `worker/tools/exceptions.py` (lines 1-37) - Why: Exception hierarchy pattern to follow
- `worker/tools/__init__.py` (lines 1-6) - Why: Tool registration pattern
- `worker/tests/test_python_tool.py` (lines 1-44) - Why: Test pattern with AsyncMock and pytest-asyncio

### New Files to Create

- `worker/tools/web.py` - WebFetchTool implementation
- `worker/tests/test_web_tool.py` - Unit tests for web fetch tool

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [HTTPX Documentation - Async Client](https://www.python-httpx.org/async/)
  - Specific section: AsyncClient usage and context managers
  - Why: Required for implementing async HTTP requests
- [HTTPX Documentation - Timeouts](https://www.python-httpx.org/advanced/#timeout-configuration)
  - Specific section: Timeout configuration
  - Why: Proper timeout handling for network requests
- [HTTPX Documentation - Error Handling](https://www.python-httpx.org/exceptions/)
  - Specific section: Exception types
  - Why: Understanding httpx exceptions for proper error handling

### Patterns to Follow

**Naming Conventions:**
```python
# Class names: PascalCase with "Tool" suffix
class WebFetchTool(BaseTool):
    pass

# Exception names: PascalCase with "Error" suffix
class WebFetchError(ToolError):
    pass

# Method names: snake_case
async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
    pass
```

**Error Handling:**
```python
# From python.py:58-61
if timeout <= 0 or timeout > 300:
    raise PythonExecutionError(f"Invalid timeout: {timeout}. Must be between 1 and 300 seconds")

# From python.py:80-81
except Exception as e:
    raise PythonExecutionError(f"Failed to execute Python code: {e}") from e
```

**Logging Pattern:**
```python
# From base.py:28-34
def _log_execution(self, params: Dict[str, Any]):
    """Log tool execution."""
    self.logger.info("tool_execution_started", params=params)

def _log_result(self, result: Dict[str, Any]):
    """Log tool result."""
    self.logger.info("tool_execution_completed", result=result)
```

**Tool Structure:**
```python
# From python.py:30-56
async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool with parameters.

    Args:
        params: {
            "param1": type - description,
            "param2": type (optional) - description (default: value)
        }

    Returns:
        {
            "key1": type,
            "key2": type
        }
    """
    self._log_execution(params)
    # Validate required params
    # Call internal method
    result = await self.run(...)
    self._log_result(result)
    return result
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create exception classes and base structure for WebFetchTool.

**Tasks:**
- Add WebFetchError and WebFetchTimeoutError to exceptions.py
- Create web.py with WebFetchTool class skeleton

### Phase 2: Core Implementation

Implement HTTP request functionality with GET/POST support and JSON parsing.

**Tasks:**
- Implement execute() method with parameter validation
- Implement fetch() method with httpx.AsyncClient
- Add timeout handling and error management
- Implement JSON response parsing

### Phase 3: Integration

Register the new tool in the tools module.

**Tasks:**
- Update tools/__init__.py to export WebFetchTool
- Verify import structure

### Phase 4: Testing & Validation

Create comprehensive unit tests and validate implementation.

**Tasks:**
- Implement unit tests for GET requests
- Implement unit tests for POST requests
- Implement unit tests for error cases
- Run full test suite and validation

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: UPDATE worker/tools/exceptions.py

- **IMPLEMENT**: Add WebFetchError and WebFetchTimeoutError exception classes
- **PATTERN**: Follow existing exception pattern (lines 29-36)
- **IMPORTS**: None needed
- **CODE**:
```python
class WebFetchError(ToolError):
    """Web fetch operation failed."""
    pass


class WebFetchTimeoutError(WebFetchError):
    """Web fetch request timed out."""
    pass
```
- **VALIDATE**: `cd worker && python -c "from tools.exceptions import WebFetchError, WebFetchTimeoutError; print('OK')"`

### Task 2: CREATE worker/tools/web.py

- **IMPLEMENT**: Create WebFetchTool class with execute() and fetch() methods
- **PATTERN**: Mirror python.py structure (lines 1-82)
- **IMPORTS**: httpx, time, structlog, typing, base, exceptions
- **FEATURES**:
  - Support GET and POST methods
  - JSON response parsing with fallback to text
  - Timeout validation (1-300 seconds, default 30)
  - Request/response logging
  - Proper error handling for network issues
- **GOTCHA**: Use async context manager for httpx.AsyncClient
- **GOTCHA**: Handle both JSON and non-JSON responses gracefully
- **CODE STRUCTURE**:
```python
"""Web fetch tool for HTTP requests."""
from typing import Any, Dict, Optional
import time
import httpx
import structlog
from .base import BaseTool
from .exceptions import WebFetchError, WebFetchTimeoutError

logger = structlog.get_logger()


class WebFetchTool(BaseTool):
    """Fetch data from web URLs via HTTP."""

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute web fetch request.

        Args:
            params: {
                "url": str - URL to fetch,
                "method": str (optional) - HTTP method GET/POST (default: GET),
                "headers": dict (optional) - HTTP headers,
                "data": dict (optional) - Request body for POST,
                "timeout": int (optional) - Timeout in seconds (default: 30)
            }

        Returns:
            {
                "success": bool,
                "status_code": int,
                "body": str,
                "json": dict | None,
                "headers": dict,
                "execution_time": float
            }
        """
        self._log_execution(params)

        url = params.get("url")
        if not url:
            raise WebFetchError("URL is required")

        method = params.get("method", "GET").upper()
        if method not in ["GET", "POST"]:
            raise WebFetchError(f"Unsupported method: {method}. Only GET and POST are supported")

        timeout = params.get("timeout", 30)
        if timeout <= 0 or timeout > 300:
            raise WebFetchError(f"Invalid timeout: {timeout}. Must be between 1 and 300 seconds")

        headers = params.get("headers", {})
        data = params.get("data")

        result = await self.fetch(url, method, headers, data, timeout)
        self._log_result(result)
        return result

    async def fetch(self, url: str, method: str, headers: Dict[str, str],
                   data: Optional[Dict[str, Any]], timeout: int) -> Dict[str, Any]:
        """Perform HTTP request."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                else:  # POST
                    response = await client.post(url, headers=headers, json=data)

                execution_time = time.time() - start_time

                # Try to parse JSON, fallback to text
                json_data = None
                try:
                    json_data = response.json()
                except Exception:
                    pass

                return {
                    "success": response.is_success,
                    "status_code": response.status_code,
                    "body": response.text,
                    "json": json_data,
                    "headers": dict(response.headers),
                    "execution_time": execution_time
                }
        except httpx.TimeoutException as e:
            raise WebFetchTimeoutError(f"Request timed out after {timeout}s: {e}") from e
        except Exception as e:
            raise WebFetchError(f"Failed to fetch URL: {e}") from e
```
- **VALIDATE**: `cd worker && python -c "from tools.web import WebFetchTool; print('OK')"`

### Task 3: UPDATE worker/tools/__init__.py

- **IMPLEMENT**: Export WebFetchTool
- **PATTERN**: Follow existing export pattern (lines 1-5)
- **IMPORTS**: Add WebFetchTool import
- **CODE**:
```python
"""Tool implementations."""
from .browser import BrowserTool
from .python import PythonTool
from .web import WebFetchTool

__all__ = ["BrowserTool", "PythonTool", "WebFetchTool"]
```
- **VALIDATE**: `cd worker && python -c "from tools import WebFetchTool; print('OK')"`

### Task 4: CREATE worker/tests/test_web_tool.py

- **IMPLEMENT**: Comprehensive unit tests for WebFetchTool
- **PATTERN**: Mirror test_python_tool.py structure (lines 1-44)
- **IMPORTS**: pytest, AsyncMock, httpx, WebFetchTool, WebFetchError
- **TEST CASES**:
  1. Successful GET request with JSON response
  2. Successful POST request with JSON data
  3. Non-JSON response handling
  4. HTTP error status codes (404, 500)
  5. Timeout error
  6. Missing URL parameter
  7. Invalid HTTP method
  8. Invalid timeout value
- **CODE**:
```python
"""Unit tests for Web Fetch tool."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tools.web import WebFetchTool, WebFetchError, WebFetchTimeoutError
import httpx


@pytest.mark.asyncio
async def test_web_fetch_get_success():
    """Test successful GET request with JSON response."""
    tool = WebFetchTool()

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.text = '{"result": "success"}'
    mock_response.json.return_value = {"result": "success"}
    mock_response.headers = {"content-type": "application/json"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await tool.execute({
            "url": "https://api.example.com/data",
            "method": "GET"
        })

    assert result["success"] is True
    assert result["status_code"] == 200
    assert result["json"] == {"result": "success"}
    assert result["execution_time"] >= 0


@pytest.mark.asyncio
async def test_web_fetch_post_success():
    """Test successful POST request with data."""
    tool = WebFetchTool()

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 201
    mock_response.text = '{"id": 123}'
    mock_response.json.return_value = {"id": 123}
    mock_response.headers = {"content-type": "application/json"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        result = await tool.execute({
            "url": "https://api.example.com/create",
            "method": "POST",
            "data": {"name": "test"}
        })

    assert result["success"] is True
    assert result["status_code"] == 201
    assert result["json"]["id"] == 123


@pytest.mark.asyncio
async def test_web_fetch_non_json_response():
    """Test handling of non-JSON response."""
    tool = WebFetchTool()

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.text = "<html>Hello World</html>"
    mock_response.json.side_effect = ValueError("Not JSON")
    mock_response.headers = {"content-type": "text/html"}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await tool.execute({"url": "https://example.com"})

    assert result["success"] is True
    assert result["json"] is None
    assert "<html>" in result["body"]


@pytest.mark.asyncio
async def test_web_fetch_http_error():
    """Test handling of HTTP error status."""
    tool = WebFetchTool()

    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.json.side_effect = ValueError("Not JSON")
    mock_response.headers = {}

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await tool.execute({"url": "https://example.com/notfound"})

    assert result["success"] is False
    assert result["status_code"] == 404


@pytest.mark.asyncio
async def test_web_fetch_timeout():
    """Test timeout handling."""
    tool = WebFetchTool()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(WebFetchTimeoutError, match="timed out"):
            await tool.execute({"url": "https://slow.example.com", "timeout": 5})


@pytest.mark.asyncio
async def test_web_fetch_missing_url():
    """Test execution without URL parameter."""
    tool = WebFetchTool()

    with pytest.raises(WebFetchError, match="URL is required"):
        await tool.execute({})


@pytest.mark.asyncio
async def test_web_fetch_invalid_method():
    """Test invalid HTTP method."""
    tool = WebFetchTool()

    with pytest.raises(WebFetchError, match="Unsupported method"):
        await tool.execute({"url": "https://example.com", "method": "DELETE"})


@pytest.mark.asyncio
async def test_web_fetch_invalid_timeout():
    """Test invalid timeout value."""
    tool = WebFetchTool()

    with pytest.raises(WebFetchError, match="Invalid timeout"):
        await tool.execute({"url": "https://example.com", "timeout": 500})
```
- **VALIDATE**: `cd worker && uv run pytest tests/test_web_tool.py -v`

---

## TESTING STRATEGY

### Unit Tests

**Framework**: pytest with pytest-asyncio
**Location**: worker/tests/test_web_tool.py
**Coverage Target**: 100% of web.py

**Test Categories**:

1. **Success Cases**
   - GET request with JSON response
   - POST request with JSON data
   - Non-JSON response handling (HTML, plain text)
   - Custom headers support

2. **Error Cases**
   - HTTP error status codes (404, 500)
   - Network timeout
   - Connection errors
   - Invalid URL format

3. **Validation Cases**
   - Missing required URL parameter
   - Invalid HTTP method (PUT, DELETE, PATCH)
   - Invalid timeout values (negative, zero, >300)

4. **Edge Cases**
   - Empty response body
   - Large response bodies
   - Malformed JSON responses

**Mocking Strategy**:
- Use `unittest.mock.patch` to mock `httpx.AsyncClient`
- Mock response objects with `MagicMock` for status_code, text, json(), headers
- Mock exceptions for timeout and network errors

### Integration Tests

Not required for this feature - unit tests with mocked HTTP client are sufficient.

### Edge Cases

- **Empty URL**: Should raise WebFetchError
- **Timeout boundary**: Test timeout=1 and timeout=300 (valid boundaries)
- **JSON parse failure**: Should return json=None, not crash
- **Non-2xx status codes**: Should return success=False but not raise exception
- **Network errors**: Should raise WebFetchError with descriptive message

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd worker && python -c "from tools.web import WebFetchTool; from tools.exceptions import WebFetchError, WebFetchTimeoutError; print('Import check: OK')"
```

**Expected**: "Import check: OK"

### Level 2: Unit Tests

```bash
cd worker && uv run pytest tests/test_web_tool.py -v
```

**Expected**: All 8 tests pass

```bash
cd worker && uv run pytest tests/test_web_tool.py --cov=tools.web --cov-report=term-missing
```

**Expected**: 100% coverage on tools/web.py

### Level 3: Full Test Suite

```bash
cd worker && uv run pytest tests/ -v
```

**Expected**: All tests pass (previous 89 + new 8 = 97 tests)

### Level 4: Manual Validation

Test with real HTTP requests (optional, for verification):

```bash
cd worker && python -c "
import asyncio
from tools.web import WebFetchTool

async def test():
    tool = WebFetchTool()
    result = await tool.execute({
        'url': 'https://httpbin.org/get',
        'method': 'GET'
    })
    print(f'Status: {result[\"status_code\"]}')
    print(f'Success: {result[\"success\"]}')
    print(f'Has JSON: {result[\"json\"] is not None}')

asyncio.run(test())
"
```

**Expected**: Status: 200, Success: True, Has JSON: True

---

## ACCEPTANCE CRITERIA

- [x] WebFetchTool implements BaseTool interface
- [x] Supports GET and POST HTTP methods
- [x] Parses JSON responses automatically
- [x] Handles non-JSON responses gracefully
- [x] Validates timeout parameter (1-300 seconds)
- [x] Validates required URL parameter
- [x] Validates HTTP method (only GET/POST)
- [x] Returns structured response with status_code, body, json, headers
- [x] Proper exception hierarchy (WebFetchError, WebFetchTimeoutError)
- [x] Uses httpx.AsyncClient with async context manager
- [x] Includes execution_time in response
- [x] Follows structlog logging pattern
- [x] 8 comprehensive unit tests covering all scenarios
- [x] 100% code coverage on web.py
- [x] All existing tests continue to pass
- [x] Tool registered in tools/__init__.py

---

## COMPLETION CHECKLIST

- [ ] Task 1: WebFetchError exceptions added to exceptions.py
- [ ] Task 2: WebFetchTool implemented in web.py
- [ ] Task 3: WebFetchTool exported in __init__.py
- [ ] Task 4: Unit tests created in test_web_tool.py
- [ ] All validation commands pass
- [ ] Full test suite passes (97 tests)
- [ ] Code coverage meets requirements (100% on web.py)
- [ ] Manual testing confirms feature works (optional)
- [ ] Code follows project conventions
- [ ] No regressions in existing functionality

---

## NOTES

### Design Decisions

1. **HTTP Methods**: Limited to GET and POST only
   - Rationale: These cover 95% of use cases for an AI agent
   - Future: Can add PUT/DELETE/PATCH if needed

2. **JSON Parsing**: Automatic with graceful fallback
   - Rationale: Most APIs return JSON, but HTML/text should also work
   - Implementation: Try json(), catch exception, return None

3. **Timeout Range**: 1-300 seconds
   - Rationale: Matches PythonTool pattern for consistency
   - 300s max prevents indefinite hangs

4. **Error Handling**: Separate timeout from general errors
   - Rationale: Timeouts are common and may need special handling
   - WebFetchTimeoutError extends WebFetchError for flexibility

5. **Response Structure**: Always return status_code, even on error
   - Rationale: HTTP errors (404, 500) are valid responses, not exceptions
   - Only network/timeout errors raise exceptions

### Security Considerations

- **URL Validation**: Basic validation (non-empty), no SSRF protection
  - Note: In production, consider blocking private IP ranges
- **Header Injection**: httpx handles header sanitization
- **Timeout**: Enforced to prevent resource exhaustion

### Performance Considerations

- **Async Client**: Uses httpx.AsyncClient for non-blocking I/O
- **Context Manager**: Ensures proper connection cleanup
- **Timeout**: Default 30s prevents long-running requests

### Future Enhancements

- Add support for PUT, DELETE, PATCH methods
- Add query parameter support
- Add authentication (Bearer token, Basic auth)
- Add retry logic with exponential backoff
- Add response size limits
- Add SSRF protection (block private IPs)
- Add cookie handling
- Add file upload support (multipart/form-data)
