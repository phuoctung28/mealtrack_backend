import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any


def run_coroutine_blocking(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run a coroutine to completion from synchronous code.

    Safe regardless of whether an event loop is already running:
    - No running loop (sync context or worker thread): run directly.
    - Running loop (inside an async handler): offload to a short-lived
      worker thread so we never call asyncio.run / run_until_complete on the
      already-running loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()
