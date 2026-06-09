"""
User FCM token model for push notifications.
"""

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Index, String

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class UserFcmTokenORM(Base, BaseMixin):
    """User FCM token table for push notification delivery."""

    __tablename__ = "user_fcm_tokens"

    # User relationship
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FCM token data
    fcm_token = Column(String(255), nullable=False, unique=True)
    device_type = Column(
        Enum("ios", "android", name="device_type_enum"), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("idx_user_fcm_tokens_user_active", "user_id", "is_active"),)
