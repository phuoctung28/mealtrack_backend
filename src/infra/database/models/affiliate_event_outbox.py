"""Outbox table for durable delivery of lifecycle events to nutree-affiliate."""
from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Text

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.base import Base


class AffiliateEventOutbox(Base):
    """
    Retry-safe outbox for lifecycle events destined for nutree-affiliate.

    Rows are written in the same DB transaction as the triggering webhook handler,
    then claimed and dispatched by a cron job.  nutree-affiliate deduplicates by
    event_id, so retrying the same row is idempotent.
    """

    __tablename__ = "affiliate_event_outbox"

    id = Column(String(36), primary_key=True)

    # Idempotency key forwarded to nutree-affiliate's inbox (usually RevenueCat event id)
    event_id = Column(String(255), nullable=False, unique=True)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)

    status = Column(String(16), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("idx_aeo_status_next_attempt", "status", "next_attempt_at"),
    )
