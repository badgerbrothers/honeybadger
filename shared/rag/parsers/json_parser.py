"""JSON document parser."""
from __future__ import annotations

from .txt_parser import TxtParser


class JsonParser(TxtParser):
    """Treat JSON as text for retrieval and indexing."""

    def supported_extensions(self) -> list[str]:
        return [".json"]
