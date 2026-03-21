"""
Notification request schemas for push notification management.
"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class FcmTokenRegistrationRequest(BaseModel):
    """Request to register an FCM token."""
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    device_type: str = Field(..., description="Device type (ios or android)")
    timezone: Optional[str] = Field(
        None,
        max_length=50,
        description="IANA timezone identifier (e.g., 'America/Los_Angeles')"
    )

    @field_validator('device_type')
    @classmethod
    def validate_device_type(cls, v):
        if v not in ['ios', 'android']:
            raise ValueError('device_type must be either "ios" or "android"')
        return v


class FcmTokenDeletionRequest(BaseModel):
    """Request to delete an FCM token."""
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token to delete")


class NotificationPreferencesUpdateRequest(BaseModel):
    """Request to update notification preferences."""
    meal_reminders_enabled: Optional[bool] = Field(None, description="Enable/disable meal reminders")
    daily_summary_enabled: Optional[bool] = Field(None, description="Enable/disable daily summary notifications")

    # Meal timing (minutes from midnight: 0-1439)
    breakfast_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Breakfast reminder time (minutes from midnight)")
    lunch_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Lunch reminder time (minutes from midnight)")
    dinner_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Dinner reminder time (minutes from midnight)")

    # Daily summary timing
    daily_summary_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Daily summary time (minutes from midnight)")
