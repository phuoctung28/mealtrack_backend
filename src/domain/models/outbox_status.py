"""Domain status enum and model for the transactional outbox system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.domain.utils.timezone_utils import utc_now


class OutboxStatus(StrEnum):
    """Lifecycle states of an outbox event."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED_DEAD_LETTER = "FAILED_DEAD_LETTER"


@dataclass
class OutboxEvent:
    """Domain representation of a durable outbox event."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: OutboxStatus = OutboxStatus.PENDING
    retry_count: int = 0
    max_retries: int = 5
    next_retry_at: datetime = field(default_factory=utc_now)
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    error_log: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    processed_at: datetime | None = None

    def is_claimable(self, now: datetime) -> bool:
        """Check if row can be claimed for dispatch."""
        if self.status == OutboxStatus.PENDING and self.next_retry_at <= now:
            return True
        if (
            self.status == OutboxStatus.IN_PROGRESS
            and self.lease_expires_at is not None
            and self.lease_expires_at <= now
        ):
            return True
        return False

    def is_terminal(self) -> bool:
        """Check if outbox event has reached a final state."""
        return self.status in (OutboxStatus.COMPLETED, OutboxStatus.FAILED_DEAD_LETTER)
