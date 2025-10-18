"""
Command to update notification preferences.
"""
from dataclasses import dataclass
from typing import Optional

from src.app.events.base import Command


@dataclass
class UpdateNotificationPreferencesCommand(Command):
    """Command to update notification preferences."""
    user_id: str
    meal_reminders_enabled: Optional[bool] = None
    water_reminders_enabled: Optional[bool] = None
    sleep_reminders_enabled: Optional[bool] = None
    progress_notifications_enabled: Optional[bool] = None
    reengagement_notifications_enabled: Optional[bool] = None
    breakfast_time_minutes: Optional[int] = None
    lunch_time_minutes: Optional[int] = None
    dinner_time_minutes: Optional[int] = None
    water_reminder_interval_hours: Optional[int] = None
    sleep_reminder_time_minutes: Optional[int] = None
