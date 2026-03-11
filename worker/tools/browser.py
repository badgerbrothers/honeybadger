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
            await self.page.wait_for_selector(selector, state="visible", timeout=10000)

            if clear:
                await self.page.fill(selector, "")

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
            raise BrowserToolError("Failed to capture screenshot") from e

