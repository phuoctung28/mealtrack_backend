"""
Notification domain models for push notifications.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


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
    PROGRESS_NOTIFICATION = "progress_notification"
    REENGAGEMENT_NOTIFICATION = "reengagement_notification"
    
    def __str__(self):
        return self.value


@dataclass
class UserFcmToken:
    """
    Domain model representing a user's FCM token for push notifications.
    """
    token_id: str  # UUID as string
    user_id: str  # UUID as string
    fcm_token: str
    device_type: DeviceType
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate invariants."""
        # Validate UUID formats
        try:
            uuid.UUID(self.token_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for token_id: {self.token_id}")
        
        try:
            uuid.UUID(self.user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
        
        # Validate FCM token format (basic check)
        if not self.fcm_token or len(self.fcm_token) < 10:
            raise ValueError("FCM token must be a valid non-empty string")
    
    @classmethod
    def create_new(cls, user_id: str, fcm_token: str, device_type: DeviceType) -> 'UserFcmToken':
        """Factory method to create a new FCM token."""
        return cls(
            token_id=str(uuid.uuid4()),
            user_id=user_id,
            fcm_token=fcm_token,
            device_type=device_type,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def deactivate(self) -> 'UserFcmToken':
        """Deactivate the token."""
        return UserFcmToken(
            token_id=self.token_id,
            user_id=self.user_id,
            fcm_token=self.fcm_token,
            device_type=self.device_type,
            is_active=False,
            created_at=self.created_at,
            updated_at=datetime.now()
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "fcm_token": self.fcm_token,
            "device_type": str(self.device_type),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
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
    sleep_reminder_time_minutes: Optional[int] = None
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
        self._validate_time_minutes(self.sleep_reminder_time_minutes, "sleep_reminder_time_minutes")
        
        # Validate water interval
        if self.water_reminder_interval_hours <= 0:
            raise ValueError("water_reminder_interval_hours must be positive")
    
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
            # Default times: 8:00 AM, 12:00 PM, 6:00 PM, 10:00 PM
            breakfast_time_minutes=480,  # 8:00 AM
            lunch_time_minutes=720,      # 12:00 PM
            dinner_time_minutes=1080,    # 6:00 PM
            sleep_reminder_time_minutes=1320,  # 10:00 PM
            created_at=datetime.now(),
            updated_at=datetime.now()
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
        sleep_reminder_time_minutes: Optional[int] = None,
    ) -> 'NotificationPreferences':
        """Update notification preferences with new values."""
        # Validate time constraints before updating
        if breakfast_time_minutes is not None:
            self._validate_time_minutes(breakfast_time_minutes, "breakfast_time_minutes")
        if lunch_time_minutes is not None:
            self._validate_time_minutes(lunch_time_minutes, "lunch_time_minutes")
        if dinner_time_minutes is not None:
            self._validate_time_minutes(dinner_time_minutes, "dinner_time_minutes")
        if sleep_reminder_time_minutes is not None:
            self._validate_time_minutes(sleep_reminder_time_minutes, "sleep_reminder_time_minutes")
        
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
            sleep_reminder_time_minutes=sleep_reminder_time_minutes if sleep_reminder_time_minutes is not None else self.sleep_reminder_time_minutes,
            created_at=self.created_at,
            updated_at=datetime.now()
        )
    
    def is_notification_type_enabled(self, notification_type: NotificationType) -> bool:
        """Check if a specific notification type is enabled."""
        if notification_type == NotificationType.MEAL_REMINDER_BREAKFAST:
            return self.meal_reminders_enabled
        elif notification_type == NotificationType.MEAL_REMINDER_LUNCH:
            return self.meal_reminders_enabled
        elif notification_type == NotificationType.MEAL_REMINDER_DINNER:
            return self.meal_reminders_enabled
        elif notification_type == NotificationType.WATER_REMINDER:
            return self.water_reminders_enabled
        elif notification_type == NotificationType.SLEEP_REMINDER:
            return self.sleep_reminders_enabled
        elif notification_type == NotificationType.PROGRESS_NOTIFICATION:
            return self.progress_notifications_enabled
        elif notification_type == NotificationType.REENGAGEMENT_NOTIFICATION:
            return self.reengagement_notifications_enabled
        else:
            return False
    
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
            "sleep_reminder_time_minutes": self.sleep_reminder_time_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class PushNotification:
    """
    Domain model representing a push notification to be sent.
    """
    user_id: str  # UUID as string
    title: str
    body: str
    notification_type: NotificationType
    data: Optional[dict] = None
    
    def __post_init__(self):
        """Validate invariants."""
        try:
            uuid.UUID(self.user_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format for user_id: {self.user_id}")
        
        if not self.title or not self.body:
            raise ValueError("Title and body must be non-empty strings")
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "user_id": self.user_id,
            "title": self.title,
            "body": self.body,
            "notification_type": str(self.notification_type),
            "data": self.data or {},
        }
