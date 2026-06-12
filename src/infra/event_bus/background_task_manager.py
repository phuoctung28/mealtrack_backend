"""Managed background task runner — replaces raw asyncio.create_task."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def spawn(self, name: str, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
        """Schedule *coro* as a tracked background task named *name*."""
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._on_done)
        return task

    def _on_done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and (exc := task.exception()):
            logger.error(
                "Background task %r failed: %s", task.get_name(), exc, exc_info=exc
            )

    async def drain(self, timeout: float = 5.0) -> None:
        """Wait for all running tasks to complete, up to *timeout* seconds."""
        if not self._tasks:
            return
        pending = list(self._tasks)
        _, still_running = await asyncio.wait(pending, timeout=timeout)
        if still_running:
            for task in still_running:
                task.cancel()
                logger.warning(
                    "Background task %r cancelled at shutdown", task.get_name()
                )
            # Await cancellation so tasks release DB connections before engine.dispose().
            await asyncio.gather(*still_running, return_exceptions=True)

    async def cancel_all(self) -> None:
        """Cancel all tracked tasks immediately."""
        snapshot = list(self._tasks)
        for task in snapshot:
            task.cancel()
        if snapshot:
            await asyncio.gather(*snapshot, return_exceptions=True)
