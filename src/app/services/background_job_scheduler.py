"""Small application seam for non-critical post-commit work."""

from __future__ import annotations

import logging
from collections.abc import Coroutine
from typing import Any


def schedule_background_job(
    task_manager: Any | None,
    name: str,
    job: Coroutine[Any, Any, Any],
    *,
    logger: logging.Logger,
) -> bool:
    """Queue a job on the managed runner without falling back to inline work."""

    if task_manager is None:
        job.close()
        logger.error("Background job dropped without a task manager: %s", name)
        return False
    try:
        task_manager.spawn(name, job)
        return True
    except Exception:
        job.close()
        logger.exception("Failed to enqueue background job: %s", name)
        return False
