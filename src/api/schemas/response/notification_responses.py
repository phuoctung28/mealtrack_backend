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
    daily_summary_enabled: bool = Field(..., description="Whether daily summary notifications are enabled")

    # Meal timing (minutes from midnight: 0-1439)
    breakfast_time_minutes: Optional[int] = Field(None, description="Breakfast reminder time (minutes from midnight)")
    lunch_time_minutes: Optional[int] = Field(None, description="Lunch reminder time (minutes from midnight)")
    dinner_time_minutes: Optional[int] = Field(None, description="Dinner reminder time (minutes from midnight)")

    # Daily summary timing
    daily_summary_time_minutes: Optional[int] = Field(None, description="Daily summary time (minutes from midnight)")


class NotificationPreferencesUpdateResponse(BaseModel):
    """Response for notification preferences update."""
    success: bool = Field(..., description="Whether the update was successful")
    preferences: NotificationPreferencesResponse = Field(..., description="Updated notification preferences")
