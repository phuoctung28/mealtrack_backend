"""Notification sent log for deduplication across workers."""
from sqlalchemy import Column, String, DateTime, Index

from src.infra.database.config import Base
from src.domain.utils.timezone_utils import utc_now


class NotificationSentLog(Base):
    """Tracks sent notifications to prevent duplicates from multiple workers."""
    __tablename__ = 'notification_sent_log'

    # Composite natural key: user + type + minute window
    user_id = Column(String(36), nullable=False, primary_key=True)
    notification_type = Column(String(50), nullable=False, primary_key=True)
    sent_minute = Column(String(16), nullable=False, primary_key=True)
    sent_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index('ix_sent_log_cleanup', 'sent_at'),
    )
