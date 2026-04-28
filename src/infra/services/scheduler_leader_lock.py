"""
Cross-process lock so only one Uvicorn worker runs the notification scheduler.

Uses fcntl.flock on a file in /tmp (POSIX). Each worker process opens the file
and tries LOCK_EX | LOCK_NB; exactly one succeeds.

Note: This coordinates workers within a single container only. With multiple
containers/instances, each runs one scheduler unless you add Redis/DB leader
election or a dedicated job worker.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SCHEDULER_LOCK_PATH = "/tmp/mealtrack_scheduler.lock"

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]


class SchedulerLeaderLock:
    """Non-blocking exclusive lock for scheduler leader election."""

    def __init__(self) -> None:
        self._fp: Optional[object] = None

    def try_acquire(self) -> bool:
        """Return True if this process became the scheduler leader."""
        if fcntl is None:
            logger.debug(
                "fcntl unavailable; assuming single process (scheduler runs in this worker)"
            )
            return True

        try:
            fp = open(SCHEDULER_LOCK_PATH, "a+", encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not open scheduler lock file: %s", exc)
            return True

        try:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fp.close()
            return False
        except OSError as exc:
            logger.warning("Scheduler flock failed: %s", exc)
            fp.close()
            return True

        self._fp = fp
        return True

    def release(self) -> None:
        """Release the lock if held."""
        if self._fp is None:
            return
        fp = self._fp
        self._fp = None
        try:
            if fcntl is not None:
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            fp.close()
        except OSError:
            pass
