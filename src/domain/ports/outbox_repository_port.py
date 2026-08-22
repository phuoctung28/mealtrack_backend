"""Repository port for transactional outbox persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from src.domain.models.outbox_status import OutboxEvent

if TYPE_CHECKING:
    from src.domain.ports.outbox_handler_port import OutboxHandlerResult


class OutboxRepositoryPort(ABC):
    """Persistence interface for outbox event queueing, lease claiming, and cleanup."""

    @abstractmethod
    async def enqueue(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        event_id: str | None = None,
        max_retries: int = 5,
        scheduled_at: datetime | None = None,
        aggregate_type: str | None = None,
        aggregate_id: str | None = None,
    ) -> OutboxEvent | None:
        """Enqueue an outbox event atomically.

        Uses nested transaction / savepoint to ensure idempotency:
        duplicate event_id returns None without aborting outer transaction.
        """

    @abstractmethod
    async def claim_due_records(
        self,
        *,
        worker_id: str,
        batch_size: int = 50,
        lease_duration: timedelta = timedelta(seconds=60),
        now: datetime | None = None,
    ) -> list[OutboxEvent]:
        """Claim due PENDING records and expired IN_PROGRESS leases using FOR UPDATE SKIP LOCKED."""

    @abstractmethod
    async def mark_completed(
        self,
        outbox_id: str,
        *,
        processed_at: datetime | None = None,
    ) -> None:
        """Mark an outbox event as COMPLETED and release lease."""

    @abstractmethod
    async def record_failure(
        self,
        outbox_id: str,
        result: OutboxHandlerResult,
        *,
        max_retries: int | None = None,
    ) -> bool:
        """Record a failure attempt, increment retry_count, and backoff or DLQ.

        Returns True if moved to FAILED_DEAD_LETTER, False if scheduled for retry.
        """

    @abstractmethod
    async def cleanup_outbox_records(
        self,
        *,
        completed_older_than: datetime,
        dead_letter_older_than: datetime,
        batch_size: int = 500,
    ) -> dict[str, int]:
        """Purge completed and dead-lettered outbox rows older than retention windows."""

    @abstractmethod
    async def find_by_id(self, outbox_id: str) -> OutboxEvent | None:
        """Retrieve single outbox event by primary ID."""

    @abstractmethod
    async def find_by_event_id(self, event_id: str) -> OutboxEvent | None:
        """Retrieve single outbox event by deduplication event_id."""

    @abstractmethod
    async def get_by_id(self, outbox_id: str) -> OutboxEvent | None:
        """Retrieve single outbox event by primary ID."""

    @abstractmethod
    async def get_by_event_id(self, event_id: str) -> OutboxEvent | None:
        """Retrieve single outbox event by deduplication event_id."""
