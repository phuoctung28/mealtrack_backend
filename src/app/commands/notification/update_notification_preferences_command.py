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
    daily_summary_enabled: Optional[bool] = None
    breakfast_time_minutes: Optional[int] = None
    lunch_time_minutes: Optional[int] = None
    dinner_time_minutes: Optional[int] = None
    daily_summary_time_minutes: Optional[int] = None
    language: Optional[str] = None
