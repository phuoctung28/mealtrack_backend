"""
Notification preferences domain model.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.utils.timezone_utils import utc_now, format_iso_utc
from .enums import NotificationType

# Map notification types to their corresponding preference fields
NOTIFICATION_TYPE_TO_FIELD = {
    NotificationType.MEAL_REMINDER_BREAKFAST: "meal_reminders_enabled",
    NotificationType.MEAL_REMINDER_LUNCH: "meal_reminders_enabled",
    NotificationType.MEAL_REMINDER_DINNER: "meal_reminders_enabled",
    NotificationType.DAILY_SUMMARY: "daily_summary_enabled",
}


@dataclass
class NotificationPreferences:
    """
    Domain model representing a user's notification preferences.
    """
    preferences_id: str  # UUID as string
    user_id: str  # UUID as string
    meal_reminders_enabled: bool = True
    daily_summary_enabled: bool = True
    breakfast_time_minutes: Optional[int] = None  # minutes from midnight (0-1439)
    lunch_time_minutes: Optional[int] = None
    dinner_time_minutes: Optional[int] = None
    daily_summary_time_minutes: Optional[int] = 1260  # 9:00 PM default
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate invariants."""
        try:
            uuid.UUID(self.preferences_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for preferences_id: {self.preferences_id}")

        try:
            uuid.UUID(self.user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")

        self._validate_time_minutes(self.breakfast_time_minutes, "breakfast_time_minutes")
        self._validate_time_minutes(self.lunch_time_minutes, "lunch_time_minutes")
        self._validate_time_minutes(self.dinner_time_minutes, "dinner_time_minutes")
        self._validate_time_minutes(self.daily_summary_time_minutes, "daily_summary_time_minutes")

    def _validate_time_minutes(self, time_minutes: Optional[int], field_name: str):
        """Validate time in minutes from midnight."""
        if time_minutes is not None and (time_minutes < 0 or time_minutes >= 1440):
            raise ValueError(f"{field_name} must be between 0 and 1439 (minutes from midnight)")

    @classmethod
    def create_default(cls, user_id: str) -> 'NotificationPreferences':
        """Factory method to create default notification preferences."""
        return cls(
            preferences_id=str(uuid.uuid4()),
            user_id=user_id,
            meal_reminders_enabled=True,
            daily_summary_enabled=True,
            breakfast_time_minutes=480,   # 8:00 AM
            lunch_time_minutes=720,       # 12:00 PM
            dinner_time_minutes=1080,     # 6:00 PM
            daily_summary_time_minutes=1260,  # 9:00 PM
            created_at=utc_now(),
            updated_at=utc_now()
        )

    def update_preferences(
        self,
        meal_reminders_enabled: Optional[bool] = None,
        daily_summary_enabled: Optional[bool] = None,
        breakfast_time_minutes: Optional[int] = None,
        lunch_time_minutes: Optional[int] = None,
        dinner_time_minutes: Optional[int] = None,
        daily_summary_time_minutes: Optional[int] = None,
    ) -> 'NotificationPreferences':
        """Update notification preferences with new values."""
        if breakfast_time_minutes is not None:
            self._validate_time_minutes(breakfast_time_minutes, "breakfast_time_minutes")
        if lunch_time_minutes is not None:
            self._validate_time_minutes(lunch_time_minutes, "lunch_time_minutes")
        if dinner_time_minutes is not None:
            self._validate_time_minutes(dinner_time_minutes, "dinner_time_minutes")
        if daily_summary_time_minutes is not None:
            self._validate_time_minutes(daily_summary_time_minutes, "daily_summary_time_minutes")

        return NotificationPreferences(
            preferences_id=self.preferences_id,
            user_id=self.user_id,
            meal_reminders_enabled=meal_reminders_enabled if meal_reminders_enabled is not None else self.meal_reminders_enabled,
            daily_summary_enabled=daily_summary_enabled if daily_summary_enabled is not None else self.daily_summary_enabled,
            breakfast_time_minutes=breakfast_time_minutes if breakfast_time_minutes is not None else self.breakfast_time_minutes,
            lunch_time_minutes=lunch_time_minutes if lunch_time_minutes is not None else self.lunch_time_minutes,
            dinner_time_minutes=dinner_time_minutes if dinner_time_minutes is not None else self.dinner_time_minutes,
            daily_summary_time_minutes=daily_summary_time_minutes if daily_summary_time_minutes is not None else self.daily_summary_time_minutes,
            created_at=self.created_at,
            updated_at=utc_now()
        )

    def is_notification_type_enabled(self, notification_type: NotificationType) -> bool:
        """Check if a specific notification type is enabled."""
        field_name = NOTIFICATION_TYPE_TO_FIELD.get(notification_type)
        return getattr(self, field_name, False) if field_name else False

    def get_meal_reminder_time(self, meal_type: str) -> Optional[int]:
        """Get the reminder time in minutes for a specific meal type."""
        if meal_type == "breakfast":
            return self.breakfast_time_minutes
        elif meal_type == "lunch":
            return self.lunch_time_minutes
        elif meal_type == "dinner":
            return self.dinner_time_minutes
        else:
            return None

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "preferences_id": self.preferences_id,
            "user_id": self.user_id,
            "meal_reminders_enabled": self.meal_reminders_enabled,
            "daily_summary_enabled": self.daily_summary_enabled,
            "breakfast_time_minutes": self.breakfast_time_minutes,
            "lunch_time_minutes": self.lunch_time_minutes,
            "dinner_time_minutes": self.dinner_time_minutes,
            "daily_summary_time_minutes": self.daily_summary_time_minutes,
            "created_at": format_iso_utc(self.created_at),
            "updated_at": format_iso_utc(self.updated_at),
        }
