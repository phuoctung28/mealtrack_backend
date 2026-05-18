"""
Cross-process/container lock so only one app instance runs the notification scheduler.

Uses fcntl.flock on a file in /tmp (POSIX). Each worker process opens the file
and tries LOCK_EX | LOCK_NB; exactly one succeeds.

The file lock only coordinates workers inside one container, so PostgreSQL
advisory lock adds cross-container coordination for multi-replica deployments.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SCHEDULER_LOCK_PATH = "/tmp/mealtrack_scheduler.lock"
SCHEDULER_DB_LOCK_KEY = 9_145_202_605_18

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]


class SchedulerLeaderLock:
    """Non-blocking exclusive lock for scheduler leader election."""

    def __init__(self) -> None:
        self._fp: Optional[object] = None
        self._db_conn = None

    def try_acquire(self) -> bool:
        """Return True if this process became the scheduler leader."""
        if fcntl is None:
            logger.debug(
                "fcntl unavailable; assuming single process (scheduler runs in this worker)"
            )
        elif not self._try_acquire_file_lock():
            return False

        if not self._try_acquire_db_lock():
            self.release()
            return False

        return True

    def _try_acquire_file_lock(self) -> bool:
        """Acquire the local process/container lock."""
        if fcntl is None:
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

    def _try_acquire_db_lock(self) -> bool:
        """Acquire a PostgreSQL advisory lock across app containers."""
        try:
            from sqlalchemy import text

            from src.infra.database.config import engine

            if engine.dialect.name != "postgresql":
                logger.debug(
                    "Scheduler DB lock skipped for dialect=%s", engine.dialect.name
                )
                return True

            conn = engine.connect()
            acquired = conn.execute(
                text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": SCHEDULER_DB_LOCK_KEY},
            ).scalar()
            if not acquired:
                conn.close()
                return False

            self._db_conn = conn
            return True
        except Exception as exc:
            logger.warning("Scheduler DB advisory lock failed: %s", exc)
            return True

    def release(self) -> None:
        """Release the lock if held."""
        db_conn = self._db_conn
        self._db_conn = None
        if db_conn is not None:
            try:
                from sqlalchemy import text

                db_conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": SCHEDULER_DB_LOCK_KEY},
                )
            except Exception:
                pass
            try:
                db_conn.close()
            except Exception:
                pass

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
