"""Notification job queue model — replaces notification_sent_log."""
import uuid
from sqlalchemy import Column, String, Date, DateTime, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from src.infra.database.config import Base
from src.domain.utils.timezone_utils import utc_now


class NotificationORM(Base):
    """
    Pre-built notification job queue.

    Each row represents one scheduled send (user × type × date).
    UNIQUE constraint on (user_id, notification_type, scheduled_date) provides dedup.
    context JSONB: {fcm_tokens: [...], calorie_goal: int, gender: str, language_code: str}
    """
    __tablename__ = 'notifications'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    notification_type = Column(String(30), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    scheduled_for_utc = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(10), nullable=False, default='pending')
    context = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'user_id', 'notification_type', 'scheduled_date',
            name='uq_notification_per_user_type_date',
        ),
        Index(
            'idx_notifications_due',
            'scheduled_for_utc', 'status',
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            'idx_notifications_expires',
            'expires_at',
            postgresql_where=text("status != 'pending'"),
        ),
    )
