"""Compatibility wrapper around shared parser exceptions."""

from shared.rag.parsers.exceptions import FileReadError, ParseError, ParserError, UnsupportedFormatError

__all__ = ["ParserError", "UnsupportedFormatError", "ParseError", "FileReadError"]
