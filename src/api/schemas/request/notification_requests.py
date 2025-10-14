"""
Request schemas for notification endpoints.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class NotificationPreferencesUpdateRequest(BaseModel):
    """Request to update notification preferences"""
    notifications_enabled: Optional[bool] = Field(None, description="Master notification toggle")
    push_notifications_enabled: Optional[bool] = Field(None, description="Push notification toggle")
    email_notifications_enabled: Optional[bool] = Field(None, description="Email notification toggle")
    weekly_weight_reminder_enabled: Optional[bool] = Field(None, description="Weekly weight reminder toggle")
    weekly_weight_reminder_day: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Sunday, 6=Saturday)")
    weekly_weight_reminder_time: Optional[str] = Field(None, description="Time in HH:mm format")
    
    @validator('weekly_weight_reminder_time')
    def validate_time_format(cls, v):
        """Validate time format"""
        if v is not None:
            if ':' not in v or len(v) != 5:
                raise ValueError('Time must be in HH:mm format')
            try:
                hours, minutes = v.split(':')
                hour = int(hours)
                minute = int(minutes)
                if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                    raise ValueError('Invalid time values')
            except ValueError as e:
                raise ValueError(f'Invalid time format: {e}')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "notifications_enabled": True,
                "push_notifications_enabled": True,
                "email_notifications_enabled": False,
                "weekly_weight_reminder_enabled": True,
                "weekly_weight_reminder_day": 0,
                "weekly_weight_reminder_time": "09:00"
            }
        }


class DeviceTokenRegisterRequest(BaseModel):
    """Request to register device token"""
    device_token: str = Field(..., description="FCM/APNs device token")
    platform: str = Field(..., description="Device platform: ios, android, web")
    device_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Device information")
    
    @validator('platform')
    def validate_platform(cls, v):
        """Validate platform"""
        if v not in ['ios', 'android', 'web']:
            raise ValueError('Platform must be one of: ios, android, web')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_token": "fK7xY9dH3mN...",
                "platform": "ios",
                "device_info": {
                    "model": "iPhone 14 Pro",
                    "os_version": "17.0",
                    "app_version": "1.2.0"
                }
            }
        }


class TestNotificationRequest(BaseModel):
    """Request to send test notification"""
    notification_type: str = Field(..., description="Type of notification to test")
    delivery_method: str = Field("push", description="Delivery method: push or email")
    
    @validator('notification_type')
    def validate_notification_type(cls, v):
        """Validate notification type"""
        valid_types = ['weight_reminder', 'meal_reminder', 'achievement', 'goal_progress', 'social', 'system']
        if v not in valid_types:
            raise ValueError(f'Notification type must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('delivery_method')
    def validate_delivery_method(cls, v):
        """Validate delivery method"""
        if v not in ['push', 'email']:
            raise ValueError('Delivery method must be push or email')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "notification_type": "weight_reminder",
                "delivery_method": "push"
            }
        }


class AdminNotificationTriggerRequest(BaseModel):
    """Request to trigger notification to multiple users (admin only)"""
    user_ids: list[str] = Field(..., description="List of user IDs to send notification to")
    notification_type: str = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    delivery_method: str = Field("push", description="Delivery method: push or email")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional notification data")
    
    @validator('notification_type')
    def validate_notification_type(cls, v):
        """Validate notification type"""
        valid_types = ['weight_reminder', 'meal_reminder', 'achievement', 'goal_progress', 'social', 'system']
        if v not in valid_types:
            raise ValueError(f'Notification type must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('delivery_method')
    def validate_delivery_method(cls, v):
        """Validate delivery method"""
        if v not in ['push', 'email']:
            raise ValueError('Delivery method must be push or email')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": ["user1", "user2"],
                "notification_type": "system",
                "title": "App Update Available",
                "body": "Version 2.0 is now available with new features!",
                "delivery_method": "push",
                "data": {
                    "action": "update_app",
                    "version": "2.0.0"
                }
            }
        }

