"""Custom exceptions for document parsing operations."""


class ParserError(Exception):
    """Base exception for parser operations."""
    pass


class UnsupportedFormatError(ParserError):
    """Unsupported file format."""
    pass


class ParseError(ParserError):
    """Failed to parse document."""
    pass


class FileReadError(ParserError):
    """Failed to read file."""
    pass
