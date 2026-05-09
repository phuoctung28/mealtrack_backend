"""Email log model for tracking sent emails."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config import Base


class EmailLog(Base):
    """Tracks all sent emails for duplicate prevention and debugging."""

    __tablename__ = "email_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email_type = Column(String(50), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resend_message_id = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="sent")

    user = relationship("User", back_populates="email_logs")

    __table_args__ = (
        Index("idx_email_logs_user_type", "user_id", "email_type"),
        Index("idx_email_logs_sent_at", "sent_at"),
    )
