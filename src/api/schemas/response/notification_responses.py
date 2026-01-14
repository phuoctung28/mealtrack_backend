"""
Notification response schemas for push notification management.
"""
from typing import Optional

from pydantic import BaseModel, Field


class FcmTokenResponse(BaseModel):
    """Response for FCM token operations."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")


class NotificationPreferencesResponse(BaseModel):
    """Response containing notification preferences."""
    meal_reminders_enabled: bool = Field(..., description="Whether meal reminders are enabled")
    water_reminders_enabled: bool = Field(..., description="Whether water reminders are enabled")
    sleep_reminders_enabled: bool = Field(..., description="Whether sleep reminders are enabled")
    progress_notifications_enabled: bool = Field(..., description="Whether progress notifications are enabled")
    reengagement_notifications_enabled: bool = Field(..., description="Whether reengagement notifications are enabled")
    
    # Meal timing (minutes from midnight: 0-1439)
    breakfast_time_minutes: Optional[int] = Field(None, description="[DEPRECATED] Breakfast reminder time (minutes from midnight)", deprecated=True)
    lunch_time_minutes: Optional[int] = Field(None, description="Lunch reminder time (minutes from midnight)")
    dinner_time_minutes: Optional[int] = Field(None, description="[DEPRECATED] Dinner reminder time (minutes from midnight)", deprecated=True)

    # Water reminder settings
    water_reminder_interval_hours: int = Field(..., description="[DEPRECATED] Water reminder interval in hours", deprecated=True)
    
    # Sleep reminder timing
    sleep_reminder_time_minutes: Optional[int] = Field(None, description="Sleep reminder time (minutes from midnight)")


class NotificationPreferencesUpdateResponse(BaseModel):
    """Response for notification preferences update."""
    success: bool = Field(..., description="Whether the update was successful")
    preferences: NotificationPreferencesResponse = Field(..., description="Updated notification preferences")
