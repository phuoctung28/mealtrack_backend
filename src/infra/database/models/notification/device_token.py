"""
Device token model for push notifications.
"""
from sqlalchemy import Column, String, Boolean, ForeignKey, Index, CheckConstraint, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.infra.database.config import Base


class DeviceToken(Base):
    """Stores device tokens for push notifications."""
    __tablename__ = 'device_tokens'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    device_token = Column(Text, nullable=False)
    platform = Column(String(20), nullable=False)  # ios, android, web
    device_info = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "platform IN ('ios', 'android', 'web')",
            name='check_platform_valid'
        ),
        Index('idx_device_tokens_user_id', 'user_id'),
        Index('idx_device_tokens_active', 'user_id', 'is_active'),
        Index('idx_device_tokens_last_used', 'last_used_at'),
    )
    
    # Relationships
    user = relationship("User", back_populates="device_tokens")
    notification_logs = relationship("NotificationLog", back_populates="device_token")
    
    def __repr__(self) -> str:
        return f"<DeviceToken(id={self.id}, user_id={self.user_id}, platform={self.platform})>"

