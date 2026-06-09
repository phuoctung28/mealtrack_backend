"""Notification job queue model — replaces notification_sent_log."""

import uuid

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config import Base


class NotificationORM(Base):
    """
    Pre-built notification job queue.

    Each row represents one scheduled send (user × type × date).
    UNIQUE constraint on (user_id, notification_type, scheduled_date) provides dedup.
    context JSON is an immutable render snapshot. Recipient truth must come from
    normalized user_fcm_tokens at dispatch time, not from this context payload.
    """

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type = Column(String(30), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    scheduled_for_utc = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(10), nullable=False, default="pending")
    context = Column(JSON, nullable=False)
    context_schema_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "notification_type",
            "scheduled_date",
            name="uq_notification_per_user_type_date",
        ),
        Index(
            "idx_notifications_due",
            "scheduled_for_utc",
            "status",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "idx_notifications_expires",
            "expires_at",
            postgresql_where=text("status != 'pending'"),
        ),
        Index(
            "idx_notifications_user_status_date",
            "user_id",
            "status",
            "scheduled_date",
        ),
        Index(
            "idx_notifications_processing_reclaim",
            "scheduled_for_utc",
            postgresql_where=text("status = 'processing'"),
        ),
    )
