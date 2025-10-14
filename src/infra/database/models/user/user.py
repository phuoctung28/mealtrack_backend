"""
Core user model for authentication and account management.
"""
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Text, Index, Enum
from sqlalchemy.orm import relationship

from src.api.schemas.common.auth_enums import AuthProviderEnum
from src.infra.database.config import Base
from src.infra.database.models.base import BaseMixin


class User(Base, BaseMixin):
    """Core user table for authentication and account management."""
    __tablename__ = 'users'
    
    # Firebase Integration
    firebase_uid = Column(String(36), unique=True, nullable=False, index=True)
    
    # Basic Information
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Authentication & OAuth
    password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    display_name = Column(String(100), nullable=True)
    photo_url = Column(Text, nullable=True)
    provider = Column(Enum(AuthProviderEnum), nullable=False, default=AuthProviderEnum.GOOGLE)  # phone, google
    
    # Status & Activity
    is_active = Column(Boolean, default=True, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    last_accessed = Column(DateTime, default=datetime.now, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_firebase_uid', 'firebase_uid'),
        Index('idx_provider', 'provider'),
        Index('idx_onboarding_completed', 'onboarding_completed'),
    )
    
    # Relationships
    profiles = relationship("UserProfile", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    device_tokens = relationship("DeviceToken", back_populates="user", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def current_profile(self):
        """Get the current active profile."""
        return next((p for p in self.profiles if p.is_current), None)
    
    def get_active_subscription(self):
        """Get user's active subscription, if any."""
        for subscription in self.subscriptions:
            if subscription.is_active():
                return subscription
        return None
    
    def is_premium(self) -> bool:
        """
        Check if user has active premium subscription.
        
        Note: This checks local cache. For real-time validation,
        use RevenueCat API via the RevenueCatService.
        """
        return self.get_active_subscription() is not None