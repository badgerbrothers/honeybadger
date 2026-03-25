"""Compatibility import layer for shared worker DB models."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from shared.db_models import (  # type: ignore
        DocumentChunk,
        DocumentIndexJob,
        DocumentIndexStatus,
        SandboxSession,
        SandboxStatus,
        Task,
        TaskRun,
        TaskStatus,
    )
except ModuleNotFoundError:
    # Allow `cd worker && uv run ...` to resolve repo-root `shared` package.
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.append(str(repo_root))
    from shared.db_models import (  # type: ignore
        DocumentChunk,
        DocumentIndexJob,
        DocumentIndexStatus,
        SandboxSession,
        SandboxStatus,
        Task,
        TaskRun,
        TaskStatus,
    )

__all__ = [
    "DocumentChunk",
    "DocumentIndexJob",
    "DocumentIndexStatus",
    "SandboxSession",
    "SandboxStatus",
    "Task",
    "TaskRun",
    "TaskStatus",
]
