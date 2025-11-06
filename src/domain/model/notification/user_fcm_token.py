"""
User FCM token domain model.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import DeviceType


@dataclass
class UserFcmToken:
    """
    Domain model representing a user's FCM token for push notifications.
    """
    token_id: str  # UUID as string
    user_id: str  # UUID as string
    fcm_token: str
    device_type: DeviceType
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID formats
        try:
            uuid.UUID(self.token_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for token_id: {self.token_id}")
        
        try:
            uuid.UUID(self.user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
        
        # Validate FCM token format (basic check)
        if not self.fcm_token or len(self.fcm_token) < 10:
            raise ValueError("FCM token must be a valid non-empty string")
    
    @classmethod
    def create_new(cls, user_id: str, fcm_token: str, device_type: DeviceType) -> 'UserFcmToken':
        """Factory method to create a new FCM token."""
        return cls(
            token_id=str(uuid.uuid4()),
            user_id=user_id,
            fcm_token=fcm_token,
            device_type=device_type,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def deactivate(self) -> 'UserFcmToken':
        """Deactivate the token."""
        return UserFcmToken(
            token_id=self.token_id,
            user_id=self.user_id,
            fcm_token=self.fcm_token,
            device_type=self.device_type,
            is_active=False,
            created_at=self.created_at,
            updated_at=datetime.now()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "fcm_token": self.fcm_token,
            "device_type": str(self.device_type),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

