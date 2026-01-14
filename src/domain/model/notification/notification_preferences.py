"""
Notification preferences domain model.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime

from src.domain.services.timezone_utils import utc_now, format_iso_utc
from typing import Optional

from .enums import NotificationType

# Map notification types to their corresponding preference fields
NOTIFICATION_TYPE_TO_FIELD = {
    NotificationType.MEAL_REMINDER_LUNCH: "meal_reminders_enabled",
    NotificationType.WATER_REMINDER: "water_reminders_enabled",
    NotificationType.SLEEP_REMINDER: "sleep_reminders_enabled",
    NotificationType.DAILY_SUMMARY: "progress_notifications_enabled",
    NotificationType.PROGRESS_NOTIFICATION: "progress_notifications_enabled",
    NotificationType.REENGAGEMENT_NOTIFICATION: "reengagement_notifications_enabled",
}


@dataclass
class NotificationPreferences:
    """
    Domain model representing a user's notification preferences.
    """
    preferences_id: str  # UUID as string
    user_id: str  # UUID as string
    meal_reminders_enabled: bool = True
    water_reminders_enabled: bool = True
    sleep_reminders_enabled: bool = True
    progress_notifications_enabled: bool = True
    reengagement_notifications_enabled: bool = True
    breakfast_time_minutes: Optional[int] = None  # minutes from midnight (0-1439)
    lunch_time_minutes: Optional[int] = None
    dinner_time_minutes: Optional[int] = None
    water_reminder_interval_hours: int = 2
    water_reminder_time_minutes: Optional[int] = 960  # 4:00 PM default
    last_water_reminder_at: Optional[datetime] = None
    sleep_reminder_time_minutes: Optional[int] = None
    daily_summary_time_minutes: Optional[int] = 1260  # 9:00 PM default
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID formats
        try:
            uuid.UUID(self.preferences_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for preferences_id: {self.preferences_id}")
        
        try:
            uuid.UUID(self.user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
        
        # Validate time constraints
        self._validate_time_minutes(self.breakfast_time_minutes, "breakfast_time_minutes")
        self._validate_time_minutes(self.lunch_time_minutes, "lunch_time_minutes")
        self._validate_time_minutes(self.dinner_time_minutes, "dinner_time_minutes")
        self._validate_time_minutes(self.water_reminder_time_minutes, "water_reminder_time_minutes")
        self._validate_time_minutes(self.sleep_reminder_time_minutes, "sleep_reminder_time_minutes")
        self._validate_time_minutes(self.daily_summary_time_minutes, "daily_summary_time_minutes")
        
        # Validate water interval
        if self.water_reminder_interval_hours <= 0:
            raise ValueError("water_reminder_interval_hours must be positive")
    
    def _validate_time_minutes(self, time_minutes: Optional[int], field_name: str):
        """Validate time in minutes from midnight."""
        if time_minutes is not None and (time_minutes < 0 or time_minutes >= 1440):
            raise ValueError(f"{field_name} must be between 0 and 1439 (minutes from midnight)")
    
    @classmethod
    def create_default(cls, user_id: str) -> 'NotificationPreferences':
        """Factory method to create default notification preferences.
        
        All notification types are enabled by default with sensible timing defaults.
        """
        return cls(
            preferences_id=str(uuid.uuid4()),
            user_id=user_id,
            # All notification types enabled by default
            meal_reminders_enabled=True,
            water_reminders_enabled=True,
            sleep_reminders_enabled=True,
            progress_notifications_enabled=True,
            reengagement_notifications_enabled=True,
            # Default meal times: 8:00 AM, 12:00 PM, 6:00 PM, 10:00 PM
            breakfast_time_minutes=480,  # 8:00 AM
            lunch_time_minutes=720,      # 12:00 PM
            dinner_time_minutes=1080,    # 6:00 PM
            sleep_reminder_time_minutes=1320,  # 10:00 PM
            water_reminder_interval_hours=2,  # Every 2 hours
            water_reminder_time_minutes=960,  # 4:00 PM
            daily_summary_time_minutes=1260,  # 9:00 PM
            created_at=utc_now(),
            updated_at=utc_now()
        )
    
    def update_preferences(
        self,
        meal_reminders_enabled: Optional[bool] = None,
        water_reminders_enabled: Optional[bool] = None,
        sleep_reminders_enabled: Optional[bool] = None,
        progress_notifications_enabled: Optional[bool] = None,
        reengagement_notifications_enabled: Optional[bool] = None,
        breakfast_time_minutes: Optional[int] = None,
        lunch_time_minutes: Optional[int] = None,
        dinner_time_minutes: Optional[int] = None,
        water_reminder_interval_hours: Optional[int] = None,
        water_reminder_time_minutes: Optional[int] = None,
        sleep_reminder_time_minutes: Optional[int] = None,
        daily_summary_time_minutes: Optional[int] = None,
    ) -> 'NotificationPreferences':
        """Update notification preferences with new values."""
        # Validate time constraints before updating
        if breakfast_time_minutes is not None:
            self._validate_time_minutes(breakfast_time_minutes, "breakfast_time_minutes")
        if lunch_time_minutes is not None:
            self._validate_time_minutes(lunch_time_minutes, "lunch_time_minutes")
        if dinner_time_minutes is not None:
            self._validate_time_minutes(dinner_time_minutes, "dinner_time_minutes")
        if water_reminder_time_minutes is not None:
            self._validate_time_minutes(water_reminder_time_minutes, "water_reminder_time_minutes")
        if sleep_reminder_time_minutes is not None:
            self._validate_time_minutes(sleep_reminder_time_minutes, "sleep_reminder_time_minutes")
        if daily_summary_time_minutes is not None:
            self._validate_time_minutes(daily_summary_time_minutes, "daily_summary_time_minutes")

        if water_reminder_interval_hours is not None and water_reminder_interval_hours <= 0:
            raise ValueError("water_reminder_interval_hours must be positive")
        
        return NotificationPreferences(
            preferences_id=self.preferences_id,
            user_id=self.user_id,
            meal_reminders_enabled=meal_reminders_enabled if meal_reminders_enabled is not None else self.meal_reminders_enabled,
            water_reminders_enabled=water_reminders_enabled if water_reminders_enabled is not None else self.water_reminders_enabled,
            sleep_reminders_enabled=sleep_reminders_enabled if sleep_reminders_enabled is not None else self.sleep_reminders_enabled,
            progress_notifications_enabled=progress_notifications_enabled if progress_notifications_enabled is not None else self.progress_notifications_enabled,
            reengagement_notifications_enabled=reengagement_notifications_enabled if reengagement_notifications_enabled is not None else self.reengagement_notifications_enabled,
            breakfast_time_minutes=breakfast_time_minutes if breakfast_time_minutes is not None else self.breakfast_time_minutes,
            lunch_time_minutes=lunch_time_minutes if lunch_time_minutes is not None else self.lunch_time_minutes,
            dinner_time_minutes=dinner_time_minutes if dinner_time_minutes is not None else self.dinner_time_minutes,
            water_reminder_interval_hours=water_reminder_interval_hours if water_reminder_interval_hours is not None else self.water_reminder_interval_hours,
            water_reminder_time_minutes=water_reminder_time_minutes if water_reminder_time_minutes is not None else self.water_reminder_time_minutes,
            last_water_reminder_at=self.last_water_reminder_at,
            sleep_reminder_time_minutes=sleep_reminder_time_minutes if sleep_reminder_time_minutes is not None else self.sleep_reminder_time_minutes,
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
            "water_reminders_enabled": self.water_reminders_enabled,
            "sleep_reminders_enabled": self.sleep_reminders_enabled,
            "progress_notifications_enabled": self.progress_notifications_enabled,
            "reengagement_notifications_enabled": self.reengagement_notifications_enabled,
            "breakfast_time_minutes": self.breakfast_time_minutes,
            "lunch_time_minutes": self.lunch_time_minutes,
            "dinner_time_minutes": self.dinner_time_minutes,
            "water_reminder_interval_hours": self.water_reminder_interval_hours,
            "water_reminder_time_minutes": self.water_reminder_time_minutes,
            "last_water_reminder_at": format_iso_utc(self.last_water_reminder_at),
            "sleep_reminder_time_minutes": self.sleep_reminder_time_minutes,
            "daily_summary_time_minutes": self.daily_summary_time_minutes,
            "created_at": format_iso_utc(self.created_at),
            "updated_at": format_iso_utc(self.updated_at),
        }

