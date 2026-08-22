"""
Transactional Outbox Background Worker CLI & Entrypoint.

Usage:
    # Run one-shot (Render cron */1 * * * *)
    python -m src.cron.outbox_worker --once

    # Run continuous background worker daemon
    python -m src.cron.outbox_worker --continuous --poll-interval 2.0 --batch-size 50 --concurrency 10
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from datetime import timedelta

from sqlalchemy import text

from src.infra.database.config_async import AsyncSessionLocal, async_engine
from src.infra.monitoring import (
    capture_exception,
    flush_observability,
    initialize_observability,
    start_span,
)
from src.infra.services.handlers import create_default_handler_registry
from src.infra.services.outbox_dispatch_engine import OutboxDispatchEngine

logger = logging.getLogger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the outbox worker."""
    parser = argparse.ArgumentParser(description="Transactional Outbox Worker")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Run until queue is drained or max-batches reached, then exit",
    )
    mode_group.add_argument(
        "--continuous",
        action="store_true",
        default=False,
        help="Run continuously in a background polling loop",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.getenv("OUTBOX_POLL_INTERVAL_SECONDS", "2.0")),
        help="Seconds to sleep when no due records are claimed in continuous mode",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("OUTBOX_BATCH_SIZE", "50")),
        help="Number of records to claim per batch",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("OUTBOX_CONCURRENCY_LIMIT", "10")),
        help="Maximum concurrent handler executions outside DB transaction",
    )
    parser.add_argument(
        "--lease-duration",
        type=int,
        default=int(os.getenv("OUTBOX_LEASE_DURATION_SECONDS", "60")),
        help="Lease duration in seconds for claimed records",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Maximum batches to process before exit in --once mode",
    )
    return parser.parse_args(args)


async def run_worker(
    *,
    continuous: bool = False,
    poll_interval: float = 2.0,
    batch_size: int = 50,
    concurrency: int = 10,
    lease_duration: int = 60,
    max_batches: int | None = None,
    stop_event: asyncio.Event | None = None,
) -> dict[str, int]:
    """Execute outbox worker loop with graceful termination handling."""
    if stop_event is None:
        stop_event = asyncio.Event()

    # DB Warm-up check
    try:
        with start_span(
            operation="cron.outbox_worker.db_warmup",
            description="outbox worker DB connection check",
        ):
            if async_engine is None:
                raise RuntimeError("Async database engine is not initialized")
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Outbox worker DB connection failed: %s", exc)
        capture_exception(
            exc,
            context={"component": "cron.outbox_worker", "operation": "db_warmup"},
        )
        return {"claimed": 0, "completed": 0, "retried": 0, "dead_letter": 0}

    registry = create_default_handler_registry()
    engine = OutboxDispatchEngine(
        registry=registry,
        session_factory=AsyncSessionLocal,
        batch_size=batch_size,
        lease_duration=timedelta(seconds=lease_duration),
        concurrency_limit=concurrency,
    )

    total_stats = {
        "claimed": 0,
        "completed": 0,
        "retried": 0,
        "dead_letter": 0,
        "batches": 0,
    }

    if continuous:
        logger.info(
            "Starting continuous outbox worker (poll_interval=%.2fs, batch_size=%d, concurrency=%d)",
            poll_interval,
            batch_size,
            concurrency,
        )
        while not stop_event.is_set():
            stats = await engine.run_once()
            total_stats["batches"] += 1
            for k in ("claimed", "completed", "retried", "dead_letter"):
                total_stats[k] += stats.get(k, 0)

            if stats.get("claimed", 0) == 0:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=poll_interval,
                    )
                except TimeoutError:
                    pass
    else:
        logger.info(
            "Starting one-shot outbox worker (batch_size=%d, concurrency=%d, max_batches=%s)",
            batch_size,
            concurrency,
            max_batches,
        )
        while not stop_event.is_set():
            stats = await engine.run_once()
            total_stats["batches"] += 1
            for k in ("claimed", "completed", "retried", "dead_letter"):
                total_stats[k] += stats.get(k, 0)

            if stats.get("claimed", 0) == 0:
                break
            if max_batches is not None and total_stats["batches"] >= max_batches:
                break

    logger.info("Outbox worker run finished: %s", total_stats)
    return total_stats


async def main(args: list[str] | None = None) -> None:
    """Main CLI entrypoint with signal listener and telemetry flush."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    initialize_observability()

    parsed = parse_args(args)
    stop_event = asyncio.Event()

    def _request_shutdown(sig_name: str) -> None:
        logger.info(
            "%s received: draining current batch and stopping...",
            sig_name,
        )
        stop_event.set()

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: _request_shutdown(s.name),
                )
            except (NotImplementedError, RuntimeError):
                pass
    except RuntimeError:
        pass

    try:
        is_continuous = parsed.continuous or (
            os.getenv("OUTBOX_WORKER_MODE", "").lower() == "continuous"
            and not parsed.once
        )
        await run_worker(
            continuous=is_continuous,
            poll_interval=parsed.poll_interval,
            batch_size=parsed.batch_size,
            concurrency=parsed.concurrency,
            lease_duration=parsed.lease_duration,
            max_batches=parsed.max_batches,
            stop_event=stop_event,
        )
    finally:
        flush_observability(timeout=5)
        if async_engine is not None:
            await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
