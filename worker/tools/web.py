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
