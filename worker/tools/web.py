"""Web fetch tool for HTTP requests."""
import time
from typing import Any
import httpx
import structlog
from .exceptions import WebFetchError, WebFetchTimeoutError
from .tool_base import Tool, ToolResult

logger = structlog.get_logger()


class WebFetchTool(Tool):
    """Fetch data from web URLs via HTTP."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch a URL over HTTP(S) and return the response body, headers, and status."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch."},
                "method": {"type": "string", "description": "HTTP method. Supports GET or POST.", "default": "GET"},
                "headers": {"type": "object", "description": "Optional request headers."},
                "data": {"type": "object", "description": "Optional JSON body for POST requests."},
                "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 30},
            },
            "required": ["url"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute web fetch request.

        Args:
            kwargs: URL, method, headers, optional data, optional timeout.
        """
        logger.info("tool_execution_started", tool=self.name, params=kwargs)

        url = kwargs.get("url")
        if not url:
            raise WebFetchError("URL is required")

        method = kwargs.get("method", "GET").upper()
        if method not in ["GET", "POST"]:
            raise WebFetchError(f"Unsupported method: {method}. Only GET and POST are supported")

        timeout = kwargs.get("timeout", 30)
        if timeout <= 0 or timeout > 300:
            raise WebFetchError(f"Invalid timeout: {timeout}. Must be between 1 and 300 seconds")

        headers = kwargs.get("headers", {})
        data = kwargs.get("data")

        result = await self.fetch(url, method, headers, data, timeout)
        logger.info("tool_execution_completed", tool=self.name, result=result)
        output = result["body"][:4000] if result["body"] else f"HTTP {result['status_code']}"
        return ToolResult(
            success=result["success"],
            output=output,
            error=None if result["success"] else f"Request failed with status {result['status_code']}",
            metadata=result,
        )

    async def fetch(
        self,
        url: str,
        method: str,
        headers: dict[str, str],
        data: dict[str, Any] | None,
        timeout: int,
    ) -> dict[str, Any]:
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
