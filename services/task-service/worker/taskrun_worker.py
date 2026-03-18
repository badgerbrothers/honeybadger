"""Task service worker entry point."""
from __future__ import annotations

import asyncio

from worker.worker_taskrun import main


if __name__ == "__main__":
    asyncio.run(main())
