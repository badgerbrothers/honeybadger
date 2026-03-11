"""Unit tests for browser tools."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from tools.browser import BrowserTool


@pytest.mark.asyncio
@patch('tools.browser.async_playwright')
async def test_browser_open(mock_playwright):
    """Test browser.open operation."""
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

