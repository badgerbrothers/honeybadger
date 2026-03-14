"""Browser automation tools using Playwright."""
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ModuleNotFoundError:  # pragma: no cover - optional dependency in local/dev envs
    async_playwright = None
    PlaywrightTimeoutError = TimeoutError

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page
else:
    Browser = Any
    BrowserContext = Any
    Page = Any
import structlog
from .exceptions import BrowserToolError, BrowserTimeoutError, BrowserSelectorError, BrowserNavigationError
from .tool_base import Tool, ToolResult

logger = structlog.get_logger()


class BrowserTool(Tool):
    """Browser automation using Playwright."""

    def __init__(self, workspace_dir: str = "/workspace"):
        """Initialize browser tool."""
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.playwright = None
        self.workspace_dir = workspace_dir

    @property
    def name(self) -> str:
        return "browser"

    @property
    def description(self) -> str:
        return "Control a browser to open pages, click elements, type text, extract content, and capture screenshots."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["open", "click", "type", "extract", "screenshot"],
                    "description": "Browser operation to perform.",
                },
                "url": {"type": "string"},
                "selector": {"type": "string"},
                "text": {"type": "string"},
                "wait_for": {"type": "string"},
                "wait_for_navigation": {"type": "boolean"},
                "clear": {"type": "boolean"},
                "format": {"type": "string"},
                "full_page": {"type": "boolean"},
                "path": {"type": "string"},
            },
            "required": ["operation"],
        }

    async def _ensure_browser(self) -> None:
        """Lazy-start the browser for the current tool instance."""
        if self.page is not None:
            return
        if async_playwright is None:
            raise BrowserToolError("Playwright is not installed. Add `playwright` to dependencies.")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def __aenter__(self):
        """Start browser on context entry."""
        await self._ensure_browser()
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

    async def execute(self, **kwargs) -> ToolResult:
        """Execute browser tool operation.

        Args:
            kwargs: Must include operation key with value open/click/type/extract/screenshot.
        """
        logger.info("tool_execution_started", tool=self.name, params=kwargs)
        await self._ensure_browser()
        operation = kwargs.get("operation")

        if operation == "open":
            result = await self.open(kwargs)
        elif operation == "click":
            result = await self.click(kwargs)
        elif operation == "type":
            result = await self.type_text(kwargs)
        elif operation == "extract":
            result = await self.extract(kwargs)
        elif operation == "screenshot":
            result = await self.screenshot(kwargs)
        else:
            raise BrowserToolError(f"Unknown operation: {operation}")

        logger.info("tool_execution_completed", tool=self.name, result=result)
        if operation == "extract":
            output = str(result.get("content", ""))[:4000]
        elif operation == "screenshot":
            output = f"Screenshot saved to {result['path']}"
        else:
            output = result.get("title") or result.get("element_text") or "Browser operation completed."

        error = None if result.get("success", False) else "Browser operation failed"
        return ToolResult(success=result.get("success", False), output=output, error=error, metadata=result)

    async def open(self, params: dict[str, Any]) -> dict[str, Any]:
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

    async def click(self, params: dict[str, Any]) -> dict[str, Any]:
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
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)
            element = await self.page.query_selector(selector)
            element_text = await element.inner_text() if element else ""

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

    async def type_text(self, params: dict[str, Any]) -> dict[str, Any]:
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
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)

            if clear:
                await self.page.fill(selector, "")

            await self.page.type(selector, str(text))

            return {"success": True}
        except PlaywrightTimeoutError as e:
            raise BrowserTimeoutError(f"Timeout waiting for selector: {selector}") from e
        except Exception as e:
            raise BrowserSelectorError(f"Failed to type into selector: {selector}") from e

    async def extract(self, params: dict[str, Any]) -> dict[str, Any]:
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
                await self.page.wait_for_selector(selector, state="attached", timeout=10000)
                element = await self.page.query_selector(selector)

                if format_type == "html":
                    content = await element.inner_html()
                else:
                    content = await element.inner_text()
            else:
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
            raise BrowserToolError("Failed to extract content") from e

    async def screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
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
        path = params.get("path")
        if not path:
            filename = f"screenshot.{format_type}"
            path = str(Path(self.workspace_dir) / filename)
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        try:
            screenshot_bytes = await self.page.screenshot(
                full_page=full_page,
                type=format_type,
                path=path
            )

            return {
                "success": True,
                "path": path,
                "size": len(screenshot_bytes),
                "artifact": {
                    "path": path,
                    "name": Path(path).name,
                    "artifact_type": "screenshot",
                    "mime_type": f"image/{format_type}",
                    "size": len(screenshot_bytes),
                },
            }
        except Exception as e:
            raise BrowserToolError("Failed to capture screenshot") from e
