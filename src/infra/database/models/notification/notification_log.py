"""
Notification log model for tracking sent notifications.
"""
from sqlalchemy import Column, String, ForeignKey, Index, CheckConstraint, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.infra.database.config import Base


class NotificationLog(Base):
    """Stores logs of sent notifications."""
    __tablename__ = 'notification_logs'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(50), nullable=False)
    delivery_method = Column(String(20), nullable=False)  # push, email
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    data = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False)  # pending, sent, delivered, failed, opened
    device_token_id = Column(String(36), ForeignKey('device_tokens.id', ondelete='SET NULL'), nullable=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    delivered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    opened_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "delivery_method IN ('push', 'email')",
            name='check_delivery_method_valid'
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'failed', 'opened')",
            name='check_status_valid'
        ),
        CheckConstraint(
            "notification_type IN ('weight_reminder', 'meal_reminder', 'achievement', 'goal_progress', 'social', 'system')",
            name='check_notification_type_valid'
        ),
        Index('idx_notification_logs_user_id', 'user_id'),
        Index('idx_notification_logs_type', 'notification_type'),
        Index('idx_notification_logs_status', 'status'),
        Index('idx_notification_logs_created_at', 'created_at'),
        Index('idx_notification_logs_user_type', 'user_id', 'notification_type'),
    )
    
    # Relationships
    user = relationship("User", back_populates="notification_logs")
    device_token = relationship("DeviceToken", back_populates="notification_logs")
    
    def __repr__(self) -> str:
        return f"<NotificationLog(id={self.id}, type={self.notification_type}, status={self.status})>"

