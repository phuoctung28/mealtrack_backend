"""
Notification queries for event-driven architecture.
"""
from .get_notification_preferences_query import GetNotificationPreferencesQuery
from .get_user_devices_query import GetUserDevicesQuery
from .get_notification_history_query import GetNotificationHistoryQuery

__all__ = [
    'GetNotificationPreferencesQuery',
    'GetUserDevicesQuery',
    'GetNotificationHistoryQuery',
]

