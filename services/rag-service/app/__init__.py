"""rag-service application package."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "shared").exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.append(candidate_str)
            return


_ensure_repo_root_on_path()
