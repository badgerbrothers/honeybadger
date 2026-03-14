"""Unit tests for Web Fetch tool."""
import pytest
from unittest.mock import patch, MagicMock
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

        result = await tool.execute(
            url="https://api.example.com/data",
            method="GET",
        )

    assert result.success is True
    assert result.metadata["status_code"] == 200
    assert result.metadata["json"] == {"result": "success"}
    assert result.metadata["execution_time"] >= 0


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

        result = await tool.execute(
            url="https://api.example.com/create",
            method="POST",
            data={"name": "test"},
        )

    assert result.success is True
    assert result.metadata["status_code"] == 201
    assert result.metadata["json"]["id"] == 123


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

        result = await tool.execute(url="https://example.com")

    assert result.success is True
    assert result.metadata["json"] is None
    assert "<html>" in result.metadata["body"]


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

        result = await tool.execute(url="https://example.com/notfound")

    assert result.success is False
    assert result.metadata["status_code"] == 404


@pytest.mark.asyncio
async def test_web_fetch_timeout():
    """Test timeout handling."""
    tool = WebFetchTool()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(WebFetchTimeoutError, match="timed out"):
            await tool.execute(url="https://slow.example.com", timeout=5)


@pytest.mark.asyncio
async def test_web_fetch_missing_url():
    """Test execution without URL parameter."""
    tool = WebFetchTool()

    with pytest.raises(WebFetchError, match="URL is required"):
        await tool.execute()


@pytest.mark.asyncio
async def test_web_fetch_invalid_method():
    """Test invalid HTTP method."""
    tool = WebFetchTool()

    with pytest.raises(WebFetchError, match="Unsupported method"):
        await tool.execute(url="https://example.com", method="DELETE")


@pytest.mark.asyncio
async def test_web_fetch_invalid_timeout():
    """Test invalid timeout value."""
    tool = WebFetchTool()

    with pytest.raises(WebFetchError, match="Invalid timeout"):
        await tool.execute(url="https://example.com", timeout=500)
