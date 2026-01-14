"""
Notification-related enums.
"""
from enum import Enum


class DeviceType(Enum):
    """Device types for FCM tokens."""
    IOS = "ios"
    ANDROID = "android"
    
    def __str__(self):
        return self.value


class NotificationType(Enum):
    """Types of notifications that can be sent."""
    MEAL_REMINDER_BREAKFAST = "meal_reminder_breakfast"
    MEAL_REMINDER_LUNCH = "meal_reminder_lunch"
    MEAL_REMINDER_DINNER = "meal_reminder_dinner"
    WATER_REMINDER = "water_reminder"
    SLEEP_REMINDER = "sleep_reminder"
    DAILY_SUMMARY = "daily_summary"
    PROGRESS_NOTIFICATION = "progress_notification"
    REENGAGEMENT_NOTIFICATION = "reengagement_notification"

    def __str__(self):
        return self.value

