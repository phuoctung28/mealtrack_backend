"""
Database maintenance and cleanup cron entry point.

Run manually:  python -m src.cron.maintenance
Render cron schedule:  0 3 * * *  (daily at 3:00 AM UTC)

Phases:
  1. Cleanup terminal meal write operations (>30 days old)
  2. Purge expired transactional outbox records (completed > 7 days, DLQ > 30 days)
  3. Database health verification
"""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import text

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config_async import async_engine
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.monitoring import (
    capture_exception,
    flush_observability,
    initialize_observability,
    log_event,
    start_span,
)

logger = logging.getLogger(__name__)


async def cleanup_meal_write_operations(
    *,
    older_than_days: int = 30,
    batch_size: int = 500,
    max_batches: int = 10,
) -> int:
    """Purge completed/aborted meal write operations older than retention period."""
    cutoff = utc_now() - timedelta(days=older_than_days)
    total_deleted = 0

    for _ in range(max_batches):
        async with AsyncUnitOfWork() as uow:
            cleanup_fn = getattr(uow.meal_write_operations, "cleanup_finished", None)
            if cleanup_fn is None:
                break
            deleted = await cleanup_fn(older_than=cutoff, limit=batch_size)
            await uow.commit()

        total_deleted += deleted
        if deleted < batch_size:
            # Done, no more matching records
            break

    logger.info(
        "maintenance.cleanup_meal_write_operations: deleted=%d cutoff=%s",
        total_deleted,
        cutoff.isoformat(),
    )
    return total_deleted


async def cleanup_outbox_records(
    *,
    completed_older_than_days: int = 7,
    dead_letter_older_than_days: int = 30,
    batch_size: int = 500,
    max_batches: int = 10,
) -> dict[str, int]:
    """Purge completed and dead-letter outbox records older than retention period."""
    now = utc_now()
    completed_cutoff = now - timedelta(days=completed_older_than_days)
    dead_letter_cutoff = now - timedelta(days=dead_letter_older_than_days)
    total_deleted = {
        "deleted_completed": 0,
        "deleted_dead_letter": 0,
        "total_deleted": 0,
    }

    for _ in range(max_batches):
        async with AsyncUnitOfWork() as uow:
            cleanup_fn = getattr(uow.outbox, "cleanup_outbox_records", None)
            if cleanup_fn is None:
                break
            deleted = await cleanup_fn(
                completed_older_than=completed_cutoff,
                dead_letter_older_than=dead_letter_cutoff,
                batch_size=batch_size,
            )
            await uow.commit()

        total_deleted["deleted_completed"] += deleted.get("deleted_completed", 0)
        total_deleted["deleted_dead_letter"] += deleted.get("deleted_dead_letter", 0)
        total_deleted["total_deleted"] += deleted.get("total_deleted", 0)

        if deleted.get("total_deleted", 0) < batch_size:
            # Done, no more matching records
            break

    logger.info(
        "maintenance.cleanup_outbox_records: deleted=%s completed_cutoff=%s dead_letter_cutoff=%s",
        total_deleted,
        completed_cutoff.isoformat(),
        dead_letter_cutoff.isoformat(),
    )
    return total_deleted


async def run() -> None:
    """Execute all maintenance phases and gracefully exit."""
    logging.basicConfig(level=logging.INFO)
    initialize_observability()

    # DB connection check
    try:
        with start_span(operation="cron.db_warmup", description="maintenance DB check"):
            if async_engine is None:
                raise RuntimeError("Async database engine is not initialized")
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Maintenance DB connection failed: %s", exc)
        capture_exception(
            exc,
            context={"component": "cron.maintenance", "operation": "db_warmup"},
        )
        flush_observability(timeout=5)
        return

    # Phase 1: Purge old meal write operations
    try:
        with start_span(
            operation="cron.maintenance.meal_write_operations",
            description="purge old meal write operations",
        ):
            deleted = await cleanup_meal_write_operations(
                older_than_days=30, batch_size=500
            )
            log_event(
                "info",
                "cron.maintenance.completed",
                attributes={
                    "phase": "meal_write_operations",
                    "deleted_count": deleted,
                },
            )
    except Exception as exc:
        logger.exception("Phase 1 (meal write operations cleanup) failed")
        capture_exception(
            exc,
            context={
                "component": "cron.maintenance",
                "phase": "meal_write_operations",
            },
        )

    # Phase 2: Purge expired outbox records
    try:
        with start_span(
            operation="cron.maintenance.outbox_records",
            description="purge old outbox records",
        ):
            outbox_deleted = await cleanup_outbox_records(
                completed_older_than_days=7,
                dead_letter_older_than_days=30,
                batch_size=500,
            )
            log_event(
                "info",
                "cron.maintenance.completed",
                attributes={
                    "phase": "outbox_records",
                    "deleted_count": outbox_deleted["total_deleted"],
                },
            )
    except Exception as exc:
        logger.exception("Phase 2 (outbox records cleanup) failed")
        capture_exception(
            exc,
            context={
                "component": "cron.maintenance",
                "phase": "outbox_records",
            },
        )

    flush_observability(timeout=5)
    if async_engine:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
