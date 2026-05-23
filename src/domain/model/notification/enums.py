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
    DAILY_SUMMARY = "daily_summary"
    HYDRATION_REMINDER_AFTERNOON = "hydration_reminder_afternoon"
    HYDRATION_REMINDER_EVENING = "hydration_reminder_evening"

    def __str__(self):
        return self.value
