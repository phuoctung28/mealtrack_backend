"""
Notification request schemas for push notification management.
"""
from typing import Optional
from pydantic import BaseModel, Field, validator


class FcmTokenRegistrationRequest(BaseModel):
    """Request to register an FCM token."""
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    device_type: str = Field(..., description="Device type (ios or android)")
    
    @validator('device_type')
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
    water_reminders_enabled: Optional[bool] = Field(None, description="Enable/disable water reminders")
    sleep_reminders_enabled: Optional[bool] = Field(None, description="Enable/disable sleep reminders")
    progress_notifications_enabled: Optional[bool] = Field(None, description="Enable/disable progress notifications")
    reengagement_notifications_enabled: Optional[bool] = Field(None, description="Enable/disable reengagement notifications")
    
    # Meal timing (minutes from midnight: 0-1439)
    breakfast_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Breakfast reminder time (minutes from midnight)")
    lunch_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Lunch reminder time (minutes from midnight)")
    dinner_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Dinner reminder time (minutes from midnight)")
    
    # Water reminder settings
    water_reminder_interval_hours: Optional[int] = Field(None, gt=0, description="Water reminder interval in hours")
    
    # Sleep reminder timing
    sleep_reminder_time_minutes: Optional[int] = Field(None, ge=0, le=1439, description="Sleep reminder time (minutes from midnight)")
