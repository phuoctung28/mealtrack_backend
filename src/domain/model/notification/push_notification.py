"""
Push notification domain model.
"""
import uuid
from dataclasses import dataclass
from typing import Optional

from .enums import NotificationType


@dataclass
class PushNotification:
    """
    Domain model representing a push notification to be sent.
    """
    user_id: str  # UUID as string
    title: str
    body: str
    notification_type: NotificationType
    data: Optional[dict] = None
    
    def __post_init__(self):
        """Validate invariants."""
        try:
            uuid.UUID(self.user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
        
        if not self.title or not self.body:
            raise ValueError("Title and body must be non-empty strings")
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "user_id": self.user_id,
            "title": self.title,
            "body": self.body,
            "notification_type": str(self.notification_type),
            "data": self.data or {},
        }

