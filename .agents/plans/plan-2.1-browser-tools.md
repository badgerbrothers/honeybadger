# Feature: Browser Tools with Playwright

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement browser automation tools using Playwright to enable the AI agent to interact with web pages. The tools include: `browser.open` (navigate to URLs), `browser.click` (click elements), `browser.type` (input text), `browser.extract` (extract structured data), and `browser.screenshot` (capture page images). These tools run inside the Docker sandbox and return structured results to the orchestrator.

## User Story

As an AI agent
I want to automate browser interactions using Playwright
So that I can navigate websites, extract data, and capture screenshots to complete research and web automation tasks

## Problem Statement

The agent needs to interact with web content beyond simple HTTP requests. Many modern websites require JavaScript execution, user interactions (clicks, form inputs), and visual verification (screenshots). The current system lacks browser automation capabilities, limiting the agent to static content fetching.

## Solution Statement

Implement a Playwright-based browser tool system that runs in the sandbox container. Create five core browser operations (open, click, type, extract, screenshot) with proper error handling, timeout protection, and artifact generation for screenshots. The tools will integrate with the existing sandbox execution model and follow established patterns for tool implementation.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: worker/tools, worker/sandbox, Docker sandbox image
**Dependencies**: Playwright (already in pyproject.toml), Chromium browser in Docker image

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/sandbox/manager.py` (lines 1-56) - Why: Shows async execution pattern and sandbox lifecycle management
- `worker/sandbox/docker_backend.py` (lines 1-75) - Why: Docker command execution pattern to follow
- `worker/sandbox/exceptions.py` (lines 1-22) - Why: Exception hierarchy pattern for tool errors
- `worker/tests/test_sandbox_manager.py` (lines 1-85) - Why: Test pattern with pytest-asyncio and mocking
- `worker/pyproject.toml` (lines 1-29) - Why: Playwright already included, check version
- `.claude/PRD.md` (lines 429-454) - Why: Detailed browser tool specifications

### New Files to Create

- `worker/tools/browser.py` - Browser tool implementations (open, click, type, extract, screenshot)
- `worker/tools/base.py` - Base tool class with common patterns (error handling, logging)
- `worker/tools/exceptions.py` - Tool-specific exceptions
- `tests/worker/test_browser_tools.py` - Unit tests for browser tools
- `docker/sandbox-base/install-playwright.sh` - Script to install Playwright browsers in Docker

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Playwright Python Async API](https://playwright.dev/python/docs/api/class-playwright)
  - Specific section: Async API usage
  - Why: Required for async browser automation patterns
- [Playwright Browser Context](https://playwright.dev/python/docs/api/class-browsercontext)
  - Specific section: Browser context lifecycle
  - Why: Shows proper browser instance management
- [Playwright Selectors](https://playwright.dev/python/docs/selectors)
  - Specific section: CSS, text, and XPath selectors
  - Why: Needed for click, type, and extract operations
- [Playwright Screenshots](https://playwright.dev/python/docs/screenshots)
  - Specific section: Full page and element screenshots
  - Why: Required for screenshot tool implementation

### Patterns to Follow

**Naming Conventions:**
```python
# From sandbox/manager.py
class SandboxManager:  # PascalCase for classes
    async def create(self):  # snake_case for methods
        self.container_id = None  # snake_case for attributes
```

**Error Handling:**
```python
# From sandbox/exceptions.py
class SandboxError(Exception):
    """Base exception for sandbox operations."""
    pass

class SandboxExecutionError(SandboxError):
    """Failed to execute command in sandbox."""
    pass
```

**Async Patterns:**
```python
# From sandbox/manager.py lines 25-33
async def create(self):
    """Create sandbox container."""
    self.container_id = self.backend.create_container(
        image=self.image,
        mem_limit=self.mem_limit,
        cpu_quota=self.cpu_quota
    )
    self.backend.start_container(self.container_id)
    return self.container_id
```

**Testing Pattern:**
```python
# From test_sandbox_manager.py lines 9-22
@pytest.mark.asyncio
@patch('sandbox.manager.DockerBackend')
async def test_create_sandbox(mock_backend_class):
    """Test sandbox creation."""
    mock_backend = Mock()
    mock_backend.create_container.return_value = "container123"
    mock_backend_class.return_value = mock_backend

    manager = SandboxManager(task_run_id=uuid.uuid4())
    container_id = await manager.create()

    assert container_id == "container123"
    mock_backend.create_container.assert_called_once()
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create base tool infrastructure with common patterns for error handling, logging, and result formatting. This provides a consistent interface for all tool implementations.

**Tasks:**
- Define base tool class with abstract methods
- Create tool-specific exception hierarchy
- Set up logging patterns using structlog
- Define tool result schemas using Pydantic

### Phase 2: Core Browser Tool Implementation

Implement the five browser operations using Playwright's async API. Each tool manages browser lifecycle (launch, context, page) and returns structured results.

**Tasks:**
- Implement browser.open with URL navigation and wait strategies
- Implement browser.click with selector-based element interaction
- Implement browser.type for form input automation
- Implement browser.extract for structured data extraction
- Implement browser.screenshot with artifact generation

### Phase 3: Docker Integration

Update the Docker sandbox image to include Playwright and Chromium browser. Configure headless mode and necessary system dependencies.

**Tasks:**
- Update Dockerfile to install Playwright system dependencies
- Install Chromium browser in sandbox image
- Configure headless browser settings
- Test browser execution in container environment

### Phase 4: Testing & Validation

Create comprehensive unit tests with mocked Playwright components and integration tests with real browser instances.

**Tasks:**
- Write unit tests for each browser tool with mocking
- Create integration tests with actual Playwright execution
- Test error scenarios (timeouts, invalid selectors, network failures)
- Validate screenshot artifact generation

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE worker/tools/exceptions.py

- **IMPLEMENT**: Tool-specific exception hierarchy
- **PATTERN**: Mirror `worker/sandbox/exceptions.py` structure
- **IMPORTS**: None (base exceptions only)
- **GOTCHA**: Keep exception names descriptive and specific
- **VALIDATE**: `cd worker && python -c "from tools.exceptions import ToolError, BrowserToolError"`

```python
"""Custom exceptions for tool operations."""


class ToolError(Exception):
    """Base exception for tool operations."""
    pass


class BrowserToolError(ToolError):
    """Browser tool operation failed."""
    pass


class BrowserTimeoutError(BrowserToolError):
    """Browser operation timed out."""
    pass


class BrowserSelectorError(BrowserToolError):
    """Element selector not found or invalid."""
    pass


class BrowserNavigationError(BrowserToolError):
    """Failed to navigate to URL."""
    pass
```

### CREATE worker/tools/base.py

- **IMPLEMENT**: Base tool class with common patterns
- **PATTERN**: Abstract base class with async methods
- **IMPORTS**: `from abc import ABC, abstractmethod`, `import structlog`, `from typing import Any, Dict`
- **GOTCHA**: Use structlog for consistent logging across tools
- **VALIDATE**: `cd worker && python -c "from tools.base import BaseTool"`

```python
"""Base tool class with common patterns."""
from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

logger = structlog.get_logger()


class BaseTool(ABC):
    """Base class for all tool implementations."""

    def __init__(self):
        """Initialize base tool."""
        self.logger = logger.bind(tool=self.__class__.__name__)

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with given parameters.

        Args:
            params: Tool-specific parameters

        Returns:
            Tool execution result
        """
        pass

    def _log_execution(self, params: Dict[str, Any]):
        """Log tool execution."""
        self.logger.info("tool_execution_started", params=params)

    def _log_result(self, result: Dict[str, Any]):
        """Log tool result."""
        self.logger.info("tool_execution_completed", result=result)

    def _log_error(self, error: Exception):
        """Log tool error."""
        self.logger.error("tool_execution_failed", error=str(error), error_type=type(error).__name__)
```

### CREATE worker/tools/browser.py (Part 1: Setup and browser.open)

- **IMPLEMENT**: Browser tool class with Playwright integration
- **PATTERN**: Async context manager for browser lifecycle
- **IMPORTS**: `from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError`
- **GOTCHA**: Always close browser contexts to prevent memory leaks
- **VALIDATE**: `cd worker && python -c "from tools.browser import BrowserTool"`

```python
"""Browser automation tools using Playwright."""
from typing import Any, Dict, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import structlog
from .base import BaseTool
from .exceptions import BrowserToolError, BrowserTimeoutError, BrowserSelectorError, BrowserNavigationError

logger = structlog.get_logger()


class BrowserTool(BaseTool):
    """Browser automation using Playwright."""

    def __init__(self):
        """Initialize browser tool."""
        super().__init__()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def __aenter__(self):
        """Start browser on context entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close browser on context exit."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        return False

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute browser tool operation.

        Args:
            params: Must include 'operation' key with value: open, click, type, extract, screenshot

        Returns:
            Operation-specific result dictionary
        """
        self._log_execution(params)
        operation = params.get("operation")

        if operation == "open":
            result = await self.open(params)
        elif operation == "click":
            result = await self.click(params)
        elif operation == "type":
            result = await self.type_text(params)
        elif operation == "extract":
            result = await self.extract(params)
        elif operation == "screenshot":
            result = await self.screenshot(params)
        else:
            raise BrowserToolError(f"Unknown operation: {operation}")

        self._log_result(result)
        return result

    async def open(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Open URL in browser.

        Args:
            params: {
                "url": str,
                "wait_for": str (optional) - "load", "domcontentloaded", "networkidle" (default: "load")
            }

        Returns:
            {
                "success": bool,
                "title": str,
                "url": str,
                "status": int
            }
        """
        url = params.get("url")
        if not url:
            raise BrowserNavigationError("URL is required")

        wait_for = params.get("wait_for", "load")

        try:
            response = await self.page.goto(url, wait_until=wait_for, timeout=30000)
            title = await self.page.title()

            return {
                "success": True,
                "title": title,
                "url": self.page.url,
                "status": response.status if response else None
            }
        except PlaywrightTimeoutError as e:
            raise BrowserTimeoutError(f"Timeout opening URL: {url}") from e
        except Exception as e:
            raise BrowserNavigationError(f"Failed to open URL: {url}") from e

    async def click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Click element by selector.

        Args:
            params: {
                "selector": str,
                "wait_for_navigation": bool (optional, default: False)
            }

        Returns:
            {
                "success": bool,
                "element_text": str
            }
        """
        selector = params.get("selector")
        if not selector:
            raise BrowserSelectorError("Selector is required")

        wait_for_navigation = params.get("wait_for_navigation", False)

        try:
            # Wait for element to be visible
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)

            # Get element text before clicking
            element = await self.page.query_selector(selector)
            element_text = await element.inner_text() if element else ""

            # Click element
            if wait_for_navigation:
                async with self.page.expect_navigation(timeout=30000):
                    await self.page.click(selector)
            else:
                await self.page.click(selector)

            return {
                "success": True,
                "element_text": element_text
            }
        except PlaywrightTimeoutError as e:
            raise BrowserTimeoutError(f"Timeout waiting for selector: {selector}") from e
        except Exception as e:
            raise BrowserSelectorError(f"Failed to click selector: {selector}") from e

    async def type_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Type text into input field.

        Args:
            params: {
                "selector": str,
                "text": str,
                "clear": bool (optional, default: True)
            }

        Returns:
            {
                "success": bool
            }
        """
        selector = params.get("selector")
        text = params.get("text")
        clear = params.get("clear", True)

        if not selector:
            raise BrowserSelectorError("Selector is required")
        if text is None:
            raise BrowserToolError("Text is required")

        try:
            # Wait for element
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)

            # Clear existing text if requested
            if clear:
                await self.page.fill(selector, "")

            # Type text
            await self.page.type(selector, str(text))

            return {"success": True}
        except PlaywrightTimeoutError as e:
            raise BrowserTimeoutError(f"Timeout waiting for selector: {selector}") from e
        except Exception as e:
            raise BrowserSelectorError(f"Failed to type into selector: {selector}") from e

    async def extract(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data from page.

        Args:
            params: {
                "selector": str (optional),
                "format": str (optional) - "text", "html", "json" (default: "text")
            }

        Returns:
            {
                "success": bool,
                "content": str | dict
            }
        """
        selector = params.get("selector")
        format_type = params.get("format", "text")

        try:
            if selector:
                # Extract from specific element
                await self.page.wait_for_selector(selector, state="attached", timeout=10000)
                element = await self.page.query_selector(selector)

                if format_type == "html":
                    content = await element.inner_html()
                else:
                    content = await element.inner_text()
            else:
                # Extract from entire page
                if format_type == "html":
                    content = await self.page.content()
                else:
                    content = await self.page.inner_text("body")

            return {
                "success": True,
                "content": content
            }
        except PlaywrightTimeoutError as e:
            raise BrowserTimeoutError(f"Timeout waiting for selector: {selector}") from e
        except Exception as e:
            raise BrowserToolError(f"Failed to extract content") from e

    async def screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Capture page screenshot.

        Args:
            params: {
                "full_page": bool (optional, default: True),
                "format": str (optional) - "png", "jpeg" (default: "png"),
                "path": str (optional) - file path to save screenshot
            }

        Returns:
            {
                "success": bool,
                "path": str,
                "size": int (bytes)
            }
        """
        full_page = params.get("full_page", True)
        format_type = params.get("format", "png")
        path = params.get("path", "/workspace/screenshot.png")

        try:
            screenshot_bytes = await self.page.screenshot(
                full_page=full_page,
                type=format_type,
                path=path
            )

            return {
                "success": True,
                "path": path,
                "size": len(screenshot_bytes)
            }
        except Exception as e:
            raise BrowserToolError(f"Failed to capture screenshot") from e


### UPDATE worker/tools/__init__.py

- **IMPLEMENT**: Export browser tools for easy imports
- **PATTERN**: Simple module exports
- **IMPORTS**: `from .browser import BrowserTool`
- **GOTCHA**: Keep __init__.py minimal
- **VALIDATE**: `cd worker && python -c "from tools import BrowserTool"`

```python
"""Tool implementations."""
from .browser import BrowserTool

__all__ = ["BrowserTool"]
```

### UPDATE docker/sandbox-base/Dockerfile

- **IMPLEMENT**: Install Playwright and Chromium browser
- **PATTERN**: Multi-stage Docker build with system dependencies
- **IMPORTS**: N/A (Dockerfile)
- **GOTCHA**: Playwright requires specific system libraries for Chromium
- **VALIDATE**: `docker build -t badgers-sandbox:latest -f docker/sandbox-base/Dockerfile .`

```dockerfile
# Add after existing dependencies
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN pip install playwright==1.40.0
RUN playwright install chromium
```

### CREATE worker/tests/test_browser_tools.py

- **IMPLEMENT**: Unit tests for browser tools with mocking
- **PATTERN**: Mirror `test_sandbox_manager.py` structure with pytest-asyncio
- **IMPORTS**: `pytest`, `unittest.mock`, `from tools.browser import BrowserTool`
- **GOTCHA**: Mock Playwright objects to avoid actual browser launches in tests
- **VALIDATE**: `cd worker && pytest tests/test_browser_tools.py -v`

```python
"""Unit tests for browser tools."""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from tools.browser import BrowserTool
from tools.exceptions import BrowserToolError, BrowserTimeoutError, BrowserSelectorError


@pytest.mark.asyncio
@patch('tools.browser.async_playwright')
async def test_browser_open(mock_playwright):
    """Test browser.open operation."""
    # Setup mocks
    mock_page = AsyncMock()
    mock_page.goto.return_value = Mock(status=200)
    mock_page.title.return_value = "Test Page"
    mock_page.url = "https://example.com"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = AsyncMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.start.return_value = mock_pw
    mock_playwright.return_value = mock_pw

    # Test
    async with BrowserTool() as tool:
        result = await tool.open({"url": "https://example.com"})

    assert result["success"] is True
    assert result["title"] == "Test Page"
    assert result["url"] == "https://example.com"
    mock_page.goto.assert_called_once()


@pytest.mark.asyncio
@patch('tools.browser.async_playwright')
async def test_browser_click(mock_playwright):
    """Test browser.click operation."""
    mock_element = AsyncMock()
    mock_element.inner_text.return_value = "Click Me"

    mock_page = AsyncMock()
    mock_page.wait_for_selector.return_value = None
    mock_page.query_selector.return_value = mock_element
    mock_page.click.return_value = None

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = AsyncMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.start.return_value = mock_pw
    mock_playwright.return_value = mock_pw

    async with BrowserTool() as tool:
        result = await tool.click({"selector": "button.submit"})

    assert result["success"] is True
    assert result["element_text"] == "Click Me"
    mock_page.click.assert_called_once_with("button.submit")


@pytest.mark.asyncio
@patch('tools.browser.async_playwright')
async def test_browser_type(mock_playwright):
    """Test browser.type operation."""
    mock_page = AsyncMock()
    mock_page.wait_for_selector.return_value = None
    mock_page.fill.return_value = None
    mock_page.type.return_value = None

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = AsyncMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.start.return_value = mock_pw
    mock_playwright.return_value = mock_pw

    async with BrowserTool() as tool:
        result = await tool.type_text({"selector": "input[name='search']", "text": "test query"})

    assert result["success"] is True
    mock_page.type.assert_called_once_with("input[name='search']", "test query")


@pytest.mark.asyncio
@patch('tools.browser.async_playwright')
async def test_browser_extract(mock_playwright):
    """Test browser.extract operation."""
    mock_page = AsyncMock()
    mock_page.inner_text.return_value = "Page content"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = AsyncMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.start.return_value = mock_pw
    mock_playwright.return_value = mock_pw

    async with BrowserTool() as tool:
        result = await tool.extract({"format": "text"})

    assert result["success"] is True
    assert result["content"] == "Page content"


@pytest.mark.asyncio
@patch('tools.browser.async_playwright')
async def test_browser_screenshot(mock_playwright):
    """Test browser.screenshot operation."""
    mock_page = AsyncMock()
    mock_page.screenshot.return_value = b"fake_image_data"

    mock_context = AsyncMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw = AsyncMock()
    mock_pw.chromium.launch.return_value = mock_browser
    mock_pw.start.return_value = mock_pw
    mock_playwright.return_value = mock_pw

    async with BrowserTool() as tool:
        result = await tool.screenshot({"path": "/workspace/test.png"})

    assert result["success"] is True
    assert result["path"] == "/workspace/test.png"
    assert result["size"] == 15
```

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test each browser operation in isolation with mocked Playwright components

**Requirements**:
- Mock async_playwright to avoid actual browser launches
- Test success paths for all five operations
- Test error scenarios (timeouts, invalid selectors, missing parameters)
- Verify proper cleanup in context manager
- Use pytest-asyncio for async test support

### Integration Tests

**Scope**: Test browser tools with actual Playwright execution (optional, for CI/CD)

**Requirements**:
- Requires Docker environment with Chromium installed
- Test against real websites (use httpbin.org or local test server)
- Verify screenshot file generation
- Test timeout handling with slow-loading pages

### Edge Cases

- Invalid URLs (malformed, unreachable)
- Selectors that don't exist on page
- Timeout scenarios (slow networks, heavy pages)
- Multiple concurrent browser instances
- Browser crashes or unexpected closures
- Large screenshot files
- Special characters in text input

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd worker && uv run ruff check tools/
```

### Level 2: Unit Tests

```bash
cd worker && uv run pytest tests/test_browser_tools.py -v
```

### Level 3: Integration Tests

```bash
# Build Docker image with Playwright
docker build -t badgers-sandbox:latest -f docker/sandbox-base/Dockerfile .

# Verify Playwright installation
docker run --rm badgers-sandbox:latest python -c "from playwright.sync_api import sync_playwright; print('OK')"

# Verify Chromium browser
docker run --rm badgers-sandbox:latest playwright show-trace --help
```

### Level 4: Manual Validation

```python
# Test script to run manually
import asyncio
from tools.browser import BrowserTool

async def test_browser():
    async with BrowserTool() as tool:
        # Test open
        result = await tool.open({"url": "https://example.com"})
        print(f"Open: {result}")

        # Test extract
        result = await tool.extract({"format": "text"})
        print(f"Extract: {result['content'][:100]}")

        # Test screenshot
        result = await tool.screenshot({"path": "/tmp/test.png"})
        print(f"Screenshot: {result}")

asyncio.run(test_browser())
```

---

## ACCEPTANCE CRITERIA

- [ ] All five browser operations implemented (open, click, type, extract, screenshot)
- [ ] Browser tool uses async context manager for proper cleanup
- [ ] All operations handle timeouts gracefully (10-30s limits)
- [ ] Exceptions are specific and informative (BrowserTimeoutError, BrowserSelectorError, etc.)
- [ ] Unit tests pass with 100% coverage for browser.py
- [ ] Docker image includes Playwright and Chromium
- [ ] Screenshots save to /workspace/ directory
- [ ] Logging uses structlog with consistent format
- [ ] No memory leaks (browser contexts properly closed)
- [ ] Code follows project conventions (snake_case, async patterns)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit tests)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms browser operations work
- [ ] Docker image builds successfully with Playwright
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

**Design Decisions:**

1. **Context Manager Pattern**: Using `async with BrowserTool()` ensures browser cleanup even on errors
2. **Single Page Instance**: Each BrowserTool instance manages one page to keep state simple
3. **Timeout Strategy**: 10s for element waits, 30s for navigation to balance responsiveness and reliability
4. **Screenshot Storage**: Save to /workspace/ (sandbox filesystem) for isolation
5. **Error Hierarchy**: Specific exceptions (BrowserTimeoutError, BrowserSelectorError) enable better error handling

**Trade-offs:**

- **Headless Only**: No GUI mode to keep Docker image lightweight and secure
- **Single Browser Type**: Chromium only (not Firefox/WebKit) to minimize dependencies
- **No Cookie/Session Persistence**: Each tool instance starts fresh to avoid state issues
- **Synchronous Selector Waits**: Simpler than custom wait conditions, sufficient for MVP

**Future Enhancements:**

- Browser context reuse across multiple operations
- Cookie/session management for authenticated workflows
- Custom wait conditions (wait for specific text, element count)
- Network request interception and mocking
- PDF generation from pages
- Multi-tab support for parallel browsing

**Performance Considerations:**

- Browser launch takes ~2-3s, consider connection pooling for high-frequency use
- Full-page screenshots can be large (>1MB), implement size limits
- Chromium memory usage ~100-200MB per instance, enforce container limits

**Security Notes:**

- Sandbox network isolation prevents access to internal services
- No file system access outside /workspace/
- Timeout limits prevent infinite hangs
- Consider URL allowlist/blocklist for production use


