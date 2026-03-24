"""Custom exceptions for document parsing operations."""


class ParserError(Exception):
    """Base exception for parser operations."""


class UnsupportedFormatError(ParserError):
    """Unsupported file format."""


class ParseError(ParserError):
    """Failed to parse document."""


class FileReadError(ParserError):
    """Failed to read file."""
