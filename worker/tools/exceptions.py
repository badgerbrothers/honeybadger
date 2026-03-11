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


class PythonExecutionError(ToolError):
    """Python code execution failed."""
    pass


class PythonTimeoutError(PythonExecutionError):
    """Python execution timed out."""
    pass
