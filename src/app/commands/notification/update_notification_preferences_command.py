"""
Command to update user notification preferences.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateNotificationPreferencesCommand:
    """Command to update notification preferences"""
    user_id: str
    notifications_enabled: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    weekly_weight_reminder_enabled: Optional[bool] = None
    weekly_weight_reminder_day: Optional[int] = None
    weekly_weight_reminder_time: Optional[str] = None

