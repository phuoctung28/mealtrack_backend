from __future__ import annotations

import asyncio
import logging
import signal
from typing import Iterable, Optional

from src.api.base_dependencies import get_job_queue, initialize_queue_layer, shutdown_queue_layer
from src.domain.model.job_queue import JobPayload
from src.worker.job_router import JobRouter

logger = logging.getLogger(__name__)


class WorkerConsumer:
    """Long-running worker that consumes jobs from the distributed queue."""

    def __init__(
        self,
        job_types: Optional[Iterable[str]] = None,
        block_ms: int = 5000,
    ) -> None:
        self._job_types = list(job_types) if job_types is not None else [
            "meal_image_analysis",
            "meal_suggestions",
        ]
        self._block_ms = block_ms
        self._router = JobRouter()
        self._stopping = asyncio.Event()

    async def run(self) -> None:
        """Run the worker loop until a stop signal is received."""
        await initialize_queue_layer()
        queue = get_job_queue()
        if queue is None:
            logger.warning("Job queue is not enabled; worker will exit.")
            await shutdown_queue_layer()
            return

        logger.info("WorkerConsumer started for job types: %s", self._job_types)

        try:
            while not self._stopping.is_set():
                job = await queue.dequeue(self._job_types, block_ms=self._block_ms)
                if job is None:
                    continue

                await self._process_job(queue, job)
        finally:
            logger.info("WorkerConsumer stopping; shutting down queue layer.")
            await shutdown_queue_layer()

    async def _process_job(self, queue, job: JobPayload) -> None:
        logger.info(
            "Picked up job %s (type=%s, retry=%s)",
            job.job_id,
            job.job_type,
            job.retry_count,
        )

        try:
            await self._router.handle(job)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Job %s failed: %s", job.job_id, exc)
            await queue.nack(job.job_id, str(exc))
            return

        logger.info("Job %s completed successfully", job.job_id)
        await queue.ack(job.job_id)

    def request_stop(self) -> None:
        """Signal the worker loop to stop."""
        self._stopping.set()


async def run_worker_forever() -> None:
    """Helper to run WorkerConsumer with basic signal handling."""
    consumer = WorkerConsumer()

    loop = asyncio.get_running_loop()

    def _handle_signal(signame: str) -> None:
        logger.info("Received signal %s; requesting worker shutdown...", signame)
        consumer.request_stop()

    for signame in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, signame), _handle_signal, signame)
        except (RuntimeError, ValueError):
            # add_signal_handler may not be available on some platforms (e.g. Windows)
            logger.debug("Signal handler %s not installed (platform limitation)", signame)

    await consumer.run()

