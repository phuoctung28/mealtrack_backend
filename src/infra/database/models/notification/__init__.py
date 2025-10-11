"""
Notification models package
"""
from src.infra.database.models.notification.device_token import DeviceToken
from src.infra.database.models.notification.notification_log import NotificationLog

__all__ = [
    'DeviceToken',
    'NotificationLog',
]

