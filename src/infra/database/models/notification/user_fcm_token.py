"""
User FCM token model for push notifications.
"""
from sqlalchemy import Column, String, Boolean, Enum

from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class UserFcmToken(Base, BaseMixin):
    """User FCM token table for push notification delivery."""
    __tablename__ = 'user_fcm_tokens'
    
    # User relationship
    user_id = Column(String(36), nullable=False, index=True)
    
    # FCM token data
    fcm_token = Column(String(255), nullable=False, unique=True)
    device_type = Column(Enum('ios', 'android', name='device_type_enum'), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships - removed to avoid circular import issues
    
    def to_domain(self):
        """Convert database model to domain model."""
        from src.domain.model.notification import UserFcmToken as DomainUserFcmToken, DeviceType
        
        device_type = DeviceType.IOS if self.device_type == 'ios' else DeviceType.ANDROID
        
        return DomainUserFcmToken(
            token_id=self.id,
            user_id=self.user_id,
            fcm_token=self.fcm_token,
            device_type=device_type,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
