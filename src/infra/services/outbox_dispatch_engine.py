"""3-Phase Asynchronous Outbox Dispatch Engine with Concurrency & Lease Fencing."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports.outbox_handler_port import (
    OutboxEventContext,
    OutboxHandlerResult,
)
from src.infra.database.config_async import AsyncSessionLocal
from src.infra.monitoring import (
    capture_message,
    increment_metric,
    log_event,
    start_span,
)
from src.infra.repositories.outbox_repository import AsyncOutboxRepository
from src.infra.services.outbox_handler_registry import OutboxHandlerRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ClaimedOutboxItem:
    """Immutable snapshot of a claimed outbox row for decoupled processing."""

    id: str
    event_id: str
    event_type: str
    payload: dict[str, Any]
    retry_count: int
    max_retries: int
    created_at: datetime


class OutboxDispatchEngine:
    """3-Phase Asynchronous Dispatch Engine with lease fencing and bounded concurrency.

    Phase 1: Claim due/expired records in a short DB transaction (SELECT ... FOR UPDATE SKIP LOCKED).
    Phase 2: Dispatch handlers concurrently (outside any DB transaction) using an asyncio.Semaphore.
    Phase 3: Finalize status (COMPLETED / PENDING+backoff / FAILED_DEAD_LETTER) in a short DB transaction.
    """

    def __init__(
        self,
        registry: OutboxHandlerRegistry,
        *,
        session_factory: Callable[[], AsyncSession] | None = None,
        worker_id: str | None = None,
        batch_size: int = 50,
        lease_duration: timedelta = timedelta(seconds=60),
        concurrency_limit: int = 10,
    ) -> None:
        self.registry = registry
        self._session_factory = session_factory or AsyncSessionLocal
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.batch_size = batch_size
        self.lease_duration = lease_duration
        self.concurrency_limit = concurrency_limit

    async def run_once(self) -> dict[str, int]:
        """Execute one complete 3-phase claim-dispatch-finalize cycle."""
        with start_span(
            operation="outbox.dispatch_cycle",
            description="3-phase transactional outbox dispatch cycle",
        ):
            # Phase 1: Claim batch in a short DB transaction
            events_to_process = await self._phase1_claim_batch()

            if not events_to_process:
                return {
                    "claimed": 0,
                    "completed": 0,
                    "retried": 0,
                    "dead_letter": 0,
                }

            # Phase 2: Execute handlers concurrently outside any DB transaction
            dispatched_results = await self._phase2_dispatch_handlers(events_to_process)

            # Phase 3: Finalize statuses in a short DB transaction
            stats = await self._phase3_finalize_batch(dispatched_results)
            stats["claimed"] = len(events_to_process)
            return stats

    async def _phase1_claim_batch(self) -> list[_ClaimedOutboxItem]:
        """Phase 1: Acquire leases on due outbox events in a short atomic transaction."""
        if self._session_factory is None:
            raise RuntimeError("Async database session factory is not initialized")

        async with self._session_factory() as session:
            async with session.begin():
                repo = AsyncOutboxRepository(session)
                rows = await repo.claim_due_records(
                    worker_id=self.worker_id,
                    batch_size=self.batch_size,
                    lease_duration=self.lease_duration,
                )
                # Snapshot values into immutable structs before session commits & ends
                return [
                    _ClaimedOutboxItem(
                        id=r.id,
                        event_id=r.event_id,
                        event_type=r.event_type,
                        payload=dict(r.payload) if isinstance(r.payload, dict) else {},
                        retry_count=r.retry_count,
                        max_retries=r.max_retries,
                        created_at=r.created_at,
                    )
                    for r in rows
                ]

    async def _phase2_dispatch_handlers(
        self,
        items: list[_ClaimedOutboxItem],
    ) -> list[tuple[_ClaimedOutboxItem, OutboxHandlerResult]]:
        """Phase 2: Concurrently execute handlers outside DB transactions with bounded semaphore."""
        semaphore = asyncio.Semaphore(self.concurrency_limit)

        async def _dispatch_single(
            item: _ClaimedOutboxItem,
        ) -> tuple[_ClaimedOutboxItem, OutboxHandlerResult]:
            async with semaphore:
                handler = self.registry.get_or_fallback(item.event_type)
                context = OutboxEventContext(
                    outbox_id=item.id,
                    event_id=item.event_id,
                    event_type=item.event_type,
                    retry_count=item.retry_count,
                    created_at_iso=item.created_at.isoformat()
                    if hasattr(item.created_at, "isoformat")
                    else str(item.created_at),
                )
                try:
                    result = await handler.handle(item.payload, context)
                except Exception as exc:
                    logger.exception(
                        "Unhandled exception in outbox handler for id=%s event_id=%s type=%s",
                        item.id,
                        item.event_id,
                        item.event_type,
                    )
                    result = OutboxHandlerResult.transient_failure(
                        f"Unhandled handler exception: {exc}",
                        error_type=type(exc).__name__,
                    )
                return item, result

        return await asyncio.gather(*[_dispatch_single(item) for item in items])

    async def _phase3_finalize_batch(
        self,
        dispatched_results: list[tuple[_ClaimedOutboxItem, OutboxHandlerResult]],
    ) -> dict[str, int]:
        """Phase 3: Persist outcomes (complete, retry backoff, or DLQ) in a short DB transaction."""
        if self._session_factory is None:
            raise RuntimeError("Async database session factory is not initialized")

        completed_count = 0
        retried_count = 0
        dead_letter_count = 0

        async with self._session_factory() as session:
            async with session.begin():
                repo = AsyncOutboxRepository(session)
                for item, result in dispatched_results:
                    if result.success:
                        await repo.mark_completed(item.id)
                        completed_count += 1
                        increment_metric(
                            "outbox.processed",
                            attributes={
                                "component": "outbox_dispatcher",
                                "event_type": item.event_type,
                                "status": "completed",
                            },
                        )
                        log_event(
                            "info",
                            "Outbox event processed successfully",
                            attributes={
                                "component": "outbox_dispatcher",
                                "operation": "dispatch",
                                "row_id": item.id,
                                "event_id": item.event_id,
                                "event_type": item.event_type,
                                "status": "completed",
                            },
                        )
                    else:
                        is_dlq = await repo.record_failure(
                            item.id,
                            result,
                            max_retries=item.max_retries,
                        )
                        if is_dlq:
                            dead_letter_count += 1
                            increment_metric(
                                "outbox.dead_letter",
                                attributes={
                                    "component": "outbox_dispatcher",
                                    "event_type": item.event_type,
                                    "status": "failed_dead_letter",
                                },
                            )
                            log_event(
                                "error",
                                "Outbox event moved to dead-letter queue",
                                attributes={
                                    "component": "outbox_dispatcher",
                                    "operation": "dead_letter",
                                    "row_id": item.id,
                                    "event_id": item.event_id,
                                    "event_type": item.event_type,
                                    "attempt_count": item.retry_count + 1,
                                    "error_type": result.error_type or "UnknownError",
                                    "status": "failed_dead_letter",
                                },
                            )
                            capture_message(
                                f"Outbox event {item.event_id} ({item.event_type}) failed permanently: "
                                f"{result.error_message}",
                                level="error",
                                context={
                                    "component": "outbox_dispatcher",
                                    "operation": "dead_letter",
                                    "row_id": item.id,
                                    "event_id": item.event_id,
                                    "event_type": item.event_type,
                                    "attempt_count": item.retry_count + 1,
                                    "error_type": result.error_type or "UnknownError",
                                },
                            )
                        else:
                            retried_count += 1
                            increment_metric(
                                "outbox.retried",
                                attributes={
                                    "component": "outbox_dispatcher",
                                    "event_type": item.event_type,
                                    "status": "pending",
                                },
                            )
                            log_event(
                                "warning",
                                "Outbox event scheduled for retry",
                                attributes={
                                    "component": "outbox_dispatcher",
                                    "operation": "retry",
                                    "row_id": item.id,
                                    "event_id": item.event_id,
                                    "event_type": item.event_type,
                                    "attempt_count": item.retry_count + 1,
                                    "error_type": result.error_type or "UnknownError",
                                    "status": "pending",
                                },
                            )

        return {
            "completed": completed_count,
            "retried": retried_count,
            "dead_letter": dead_letter_count,
        }
