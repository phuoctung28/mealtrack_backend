"""
Response schemas for notification endpoints.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationPreferencesResponse(BaseModel):
    """Response with notification preferences"""
    user_id: str
    preferences: Dict[str, Any] = Field(
        ...,
        description="Notification preference settings"
    )
    updated_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "abc123",
                "preferences": {
                    "notifications_enabled": True,
                    "push_notifications_enabled": True,
                    "email_notifications_enabled": False,
                    "weekly_weight_reminder_enabled": True,
                    "weekly_weight_reminder_day": 0,
                    "weekly_weight_reminder_time": "09:00"
                },
                "updated_at": "2025-10-11T10:30:00Z"
            }
        }


class DeviceTokenResponse(BaseModel):
    """Response with device token information"""
    device_id: str
    user_id: str
    platform: str
    is_active: bool
    last_used_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "device_id": "device123",
                "user_id": "abc123",
                "platform": "ios",
                "is_active": True,
                "last_used_at": "2025-10-11T10:30:00Z",
                "created_at": "2025-10-01T08:00:00Z"
            }
        }


class DeviceListResponse(BaseModel):
    """Response with list of devices"""
    devices: List[DeviceTokenResponse]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "devices": [
                    {
                        "device_id": "device123",
                        "user_id": "abc123",
                        "platform": "ios",
                        "is_active": True,
                        "last_used_at": "2025-10-11T10:30:00Z",
                        "created_at": "2025-10-01T08:00:00Z"
                    }
                ],
                "total": 1
            }
        }


class NotificationLogResponse(BaseModel):
    """Response with notification log information"""
    id: str
    notification_type: str
    delivery_method: str
    title: str
    body: str
    status: str
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "notif123",
                "notification_type": "weight_reminder",
                "delivery_method": "push",
                "title": "Time to update your weight! ⚖️",
                "body": "It's been 7 days since your last update.",
                "status": "delivered",
                "sent_at": "2025-10-11T09:00:00Z",
                "delivered_at": "2025-10-11T09:00:05Z",
                "opened_at": "2025-10-11T09:15:30Z",
                "created_at": "2025-10-11T09:00:00Z"
            }
        }


class NotificationHistoryResponse(BaseModel):
    """Response with notification history"""
    notifications: List[NotificationLogResponse]
    total: int
    limit: int
    offset: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "notifications": [
                    {
                        "id": "notif123",
                        "notification_type": "weight_reminder",
                        "delivery_method": "push",
                        "title": "Time to update your weight! ⚖️",
                        "body": "It's been 7 days since your last update.",
                        "status": "delivered",
                        "sent_at": "2025-10-11T09:00:00Z",
                        "delivered_at": "2025-10-11T09:00:05Z",
                        "opened_at": "2025-10-11T09:15:30Z",
                        "created_at": "2025-10-11T09:00:00Z"
                    }
                ],
                "total": 15,
                "limit": 50,
                "offset": 0
            }
        }


class TestNotificationResponse(BaseModel):
    """Response for test notification"""
    success: bool
    message: str
    notification_ids: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Test notification sent successfully",
                "notification_ids": ["notif123"]
            }
        }


class AdminNotificationTriggerResponse(BaseModel):
    """Response for admin notification trigger"""
    job_id: str
    message: str
    target_users: int
    successful: int
    failed: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job123",
                "message": "Notification dispatch completed",
                "target_users": 100,
                "successful": 98,
                "failed": 2
            }
        }

