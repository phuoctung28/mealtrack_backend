"""
Notification database models.
"""
from .notification_preferences import NotificationPreferences
from .user_fcm_token import UserFcmToken

__all__ = [
    'NotificationPreferences',
    'UserFcmToken',
]
