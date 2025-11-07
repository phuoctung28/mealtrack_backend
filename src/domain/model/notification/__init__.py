"""
Notification domain models.

This package contains all notification-related domain models, split into separate
files for better maintainability and single responsibility principle.
"""
from .enums import DeviceType, NotificationType
from .notification_preferences import NotificationPreferences
from .push_notification import PushNotification
from .user_fcm_token import UserFcmToken

__all__ = [
    'DeviceType',
    'NotificationType',
    'UserFcmToken',
    'NotificationPreferences',
    'PushNotification',
]

