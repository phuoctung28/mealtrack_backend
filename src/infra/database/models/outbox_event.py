"""SQLAlchemy ORM model for outbox_events table."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from src.domain.models.outbox_status import OutboxEvent, OutboxStatus
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base


class TransactionalOutboxORM(Base):
    """Durable, transactional outbox record for asynchronous event dispatch."""

    __tablename__ = "outbox_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(255), nullable=False, unique=True)
    event_type = Column(String(128), nullable=False)
    aggregate_type = Column(String(64), nullable=True)
    aggregate_id = Column(String(128), nullable=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default=OutboxStatus.PENDING.value)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=5)
    next_retry_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    lease_owner = Column(String(128), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    error_log = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED_DEAD_LETTER')",
            name="ck_outbox_events_status",
        ),
        CheckConstraint("retry_count >= 0", name="ck_outbox_events_retry_count"),
        CheckConstraint("max_retries >= 0", name="ck_outbox_events_max_retries"),
        Index("idx_outbox_claim_due", "status", "next_retry_at"),
        Index("idx_outbox_stale_lease", "status", "lease_expires_at"),
        Index("idx_outbox_cleanup", "status", "updated_at"),
        Index("idx_outbox_aggregate", "aggregate_type", "aggregate_id"),
        Index("idx_outbox_event_type", "event_type"),
        UniqueConstraint("event_id", name="uq_outbox_event_id"),
    )

    def to_domain(self) -> OutboxEvent:
        """Convert ORM model to domain entity."""
        return OutboxEvent(
            id=str(self.id),
            event_id=str(self.event_id),
            event_type=str(self.event_type),
            aggregate_type=self.aggregate_type,
            aggregate_id=self.aggregate_id,
            payload=dict(self.payload or {}),
            status=OutboxStatus(self.status),
            retry_count=int(self.retry_count),
            max_retries=int(self.max_retries),
            next_retry_at=self.next_retry_at,
            lease_owner=self.lease_owner,
            lease_expires_at=self.lease_expires_at,
            error_log=list(self.error_log or []),
            created_at=self.created_at,
            updated_at=self.updated_at,
            processed_at=self.processed_at,
        )

    @classmethod
    def from_domain(cls, event: OutboxEvent) -> TransactionalOutboxORM:
        """Construct ORM model from domain entity."""
        return cls(
            id=event.id,
            event_id=event.event_id,
            event_type=event.event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload=event.payload,
            status=(
                event.status.value
                if isinstance(event.status, OutboxStatus)
                else str(event.status)
            ),
            retry_count=event.retry_count,
            max_retries=event.max_retries,
            next_retry_at=event.next_retry_at,
            lease_owner=event.lease_owner,
            lease_expires_at=event.lease_expires_at,
            error_log=event.error_log,
            created_at=event.created_at,
            updated_at=event.updated_at,
            processed_at=event.processed_at,
        )


# Alias for convenience
OutboxEventORM = TransactionalOutboxORM
