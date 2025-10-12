"""
Command to send a test notification.
"""
from dataclasses import dataclass


@dataclass
class SendTestNotificationCommand:
    """Command to send test notification"""
    user_id: str
    notification_type: str
    delivery_method: str  # 'push', 'email', 'both'

