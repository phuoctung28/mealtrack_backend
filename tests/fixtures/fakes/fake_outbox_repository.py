"""Fake in-memory implementation of OutboxRepositoryPort for testing."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from src.domain.models.outbox_status import OutboxEvent, OutboxStatus
from src.domain.ports.outbox_repository_port import OutboxRepositoryPort
from src.domain.services.outbox_backoff_service import calculate_next_retry_at
from src.domain.utils.timezone_utils import ensure_utc, utc_now

if TYPE_CHECKING:
    from src.domain.ports.outbox_handler_port import OutboxHandlerResult


class FakeOutboxRepository(OutboxRepositoryPort):
    """In-memory outbox repository for fast, deterministic unit testing."""

    def __init__(self) -> None:
        self.events: dict[str, OutboxEvent] = {}  # id -> OutboxEvent
        self.event_id_to_id: dict[str, str] = {}  # event_id -> id
        self.enqueue_calls: list[dict[str, Any]] = []

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
        now = utc_now()
        resolved_event_id = event_id or str(uuid.uuid4())

        # Simulate unique constraint / savepoint rollback on duplicate event_id
        if resolved_event_id in self.event_id_to_id:
            return None

        outbox_id = str(uuid.uuid4())
        effective_scheduled_at = (
            ensure_utc(scheduled_at) if scheduled_at is not None else now
        )

        event = OutboxEvent(
            id=outbox_id,
            event_id=resolved_event_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            status=OutboxStatus.PENDING,
            retry_count=0,
            max_retries=max_retries,
            next_retry_at=effective_scheduled_at,
            lease_owner=None,
            lease_expires_at=None,
            error_log=[],
            created_at=now,
            updated_at=now,
            processed_at=None,
        )

        self.events[outbox_id] = event
        self.event_id_to_id[resolved_event_id] = outbox_id
        self.enqueue_calls.append(
            {
                "event_id": resolved_event_id,
                "event_type": event_type,
                "payload": payload,
                "max_retries": max_retries,
                "scheduled_at": scheduled_at,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
            }
        )
        return event

    async def claim_due_records(
        self,
        *,
        worker_id: str,
        batch_size: int = 50,
        lease_duration: timedelta = timedelta(seconds=60),
        now: datetime | None = None,
    ) -> list[OutboxEvent]:
        current_time = now or utc_now()
        lease_expires_at = current_time + lease_duration

        eligible: list[OutboxEvent] = []
        for event in self.events.values():
            if event.status == OutboxStatus.PENDING and (
                event.next_retry_at <= current_time
            ):
                eligible.append(event)
            elif (
                event.status == OutboxStatus.IN_PROGRESS
                and event.lease_expires_at is not None
                and event.lease_expires_at <= current_time
            ):
                eligible.append(event)

        # Sort by next_retry_at ASC, created_at ASC
        eligible.sort(key=lambda e: (e.next_retry_at, e.created_at))
        claimed = eligible[:batch_size]

        for event in claimed:
            event.status = OutboxStatus.IN_PROGRESS
            event.lease_owner = worker_id
            event.lease_expires_at = lease_expires_at
            event.updated_at = current_time

        return claimed

    async def mark_completed(
        self,
        outbox_id: str,
        *,
        processed_at: datetime | None = None,
    ) -> None:
        now = processed_at or utc_now()
        if outbox_id in self.events:
            event = self.events[outbox_id]
            event.status = OutboxStatus.COMPLETED
            event.lease_owner = None
            event.lease_expires_at = None
            event.processed_at = now
            event.updated_at = now

    async def record_failure(
        self,
        outbox_id: str,
        result: OutboxHandlerResult,
        *,
        max_retries: int | None = None,
    ) -> bool:
        if outbox_id not in self.events:
            return False

        event = self.events[outbox_id]
        now = utc_now()
        event.retry_count += 1
        effective_max = max_retries if max_retries is not None else event.max_retries

        error_entry = {
            "attempt": event.retry_count,
            "timestamp": now.isoformat(),
            "worker_id": event.lease_owner,
            "error_type": result.error_type or "UnknownError",
            "error_message": result.error_message or "",
            "status_code": result.status_code,
            "is_transient": result.is_transient,
            "metadata": result.metadata or {},
        }

        current_log = list(event.error_log or [])
        current_log.append(error_entry)
        event.error_log = current_log[-10:]

        is_dead_letter = (not result.is_transient) or (
            event.retry_count >= effective_max
        )

        if is_dead_letter:
            event.status = OutboxStatus.FAILED_DEAD_LETTER
            event.lease_owner = None
            event.lease_expires_at = None
            event.updated_at = now
            return True
        else:
            event.status = OutboxStatus.PENDING
            event.lease_owner = None
            event.lease_expires_at = None
            event.next_retry_at = calculate_next_retry_at(event.retry_count, now=now)
            event.updated_at = now
            return False

    async def cleanup_outbox_records(
        self,
        *,
        completed_older_than: datetime,
        dead_letter_older_than: datetime,
        batch_size: int = 500,
    ) -> dict[str, int]:
        deleted_completed = 0
        deleted_dead_letter = 0

        to_delete: list[str] = []
        for outbox_id, event in list(self.events.items()):
            if (
                event.status == OutboxStatus.COMPLETED
                and event.updated_at < completed_older_than
                and deleted_completed < batch_size
            ):
                to_delete.append(outbox_id)
                deleted_completed += 1
            elif (
                event.status == OutboxStatus.FAILED_DEAD_LETTER
                and event.updated_at < dead_letter_older_than
                and deleted_dead_letter < batch_size
            ):
                to_delete.append(outbox_id)
                deleted_dead_letter += 1

        for outbox_id in to_delete:
            event = self.events.pop(outbox_id)
            if event.event_id in self.event_id_to_id:
                del self.event_id_to_id[event.event_id]

        return {
            "deleted_completed": deleted_completed,
            "deleted_dead_letter": deleted_dead_letter,
            "total_deleted": deleted_completed + deleted_dead_letter,
        }

    async def find_by_id(self, outbox_id: str) -> OutboxEvent | None:
        return self.events.get(outbox_id)

    async def find_by_event_id(self, event_id: str) -> OutboxEvent | None:
        outbox_id = self.event_id_to_id.get(event_id)
        return self.events.get(outbox_id) if outbox_id else None

    async def get_by_id(self, outbox_id: str) -> OutboxEvent | None:
        return await self.find_by_id(outbox_id)

    async def get_by_event_id(self, event_id: str) -> OutboxEvent | None:
        return await self.find_by_event_id(event_id)
