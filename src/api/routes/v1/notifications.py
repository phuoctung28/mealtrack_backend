"""
Notification API endpoints - Event-driven architecture.
Handles notification preferences, device tokens, and notification history.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request.notification_requests import (
    NotificationPreferencesUpdateRequest,
    DeviceTokenRegisterRequest,
    TestNotificationRequest
)
from src.api.schemas.response.notification_responses import (
    NotificationPreferencesResponse,
    DeviceTokenResponse,
    DeviceListResponse,
    NotificationHistoryResponse,
    TestNotificationResponse,
    NotificationLogResponse
)
from src.app.commands.notification import (
    UpdateNotificationPreferencesCommand,
    RegisterDeviceTokenCommand,
    UnregisterDeviceTokenCommand,
    SendTestNotificationCommand
)
from src.app.queries.notification import (
    GetNotificationPreferencesQuery,
    GetUserDevicesQuery,
    GetNotificationHistoryQuery
)
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/notifications", tags=["Notifications"])


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
    description="Retrieve user's notification preferences"
)
async def get_notification_preferences(
    user_id: str = Query(..., description="User ID"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get user notification preferences.
    
    Returns all notification settings including:
    - Global notification toggle
    - Push notification settings
    - Email notification settings
    - Weekly weight reminder configuration
    """
    try:
        # Create query
        query = GetNotificationPreferencesQuery(user_id=user_id)
        
        # Execute query
        preferences = await event_bus.send(query)
        
        # Return response
        return NotificationPreferencesResponse(
            user_id=user_id,
            preferences={
                "notifications_enabled": preferences.notifications_enabled,
                "push_notifications_enabled": preferences.push_notifications_enabled,
                "email_notifications_enabled": preferences.email_notifications_enabled,
                "weekly_weight_reminder_enabled": preferences.weekly_weight_reminder_enabled,
                "weekly_weight_reminder_day": preferences.weekly_weight_reminder_day,
                "weekly_weight_reminder_time": preferences.weekly_weight_reminder_time
            }
        )
    except Exception as e:
        raise handle_exception(e)


@router.put(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
    description="Update user's notification preferences"
)
async def update_notification_preferences(
    request: NotificationPreferencesUpdateRequest,
    user_id: str = Query(..., description="User ID"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Update user notification preferences.
    
    Allows updating:
    - Global notification toggle
    - Push notification settings
    - Email notification settings
    - Weekly weight reminder configuration (day and time)
    """
    try:
        # Create command
        command = UpdateNotificationPreferencesCommand(
            user_id=user_id,
            notifications_enabled=request.notifications_enabled,
            push_notifications_enabled=request.push_notifications_enabled,
            email_notifications_enabled=request.email_notifications_enabled,
            weekly_weight_reminder_enabled=request.weekly_weight_reminder_enabled,
            weekly_weight_reminder_day=request.weekly_weight_reminder_day,
            weekly_weight_reminder_time=request.weekly_weight_reminder_time
        )
        
        # Execute command
        updated_preferences = await event_bus.send(command)
        
        # Return response
        return NotificationPreferencesResponse(
            user_id=user_id,
            preferences={
                "notifications_enabled": updated_preferences.notifications_enabled,
                "push_notifications_enabled": updated_preferences.push_notifications_enabled,
                "email_notifications_enabled": updated_preferences.email_notifications_enabled,
                "weekly_weight_reminder_enabled": updated_preferences.weekly_weight_reminder_enabled,
                "weekly_weight_reminder_day": updated_preferences.weekly_weight_reminder_day,
                "weekly_weight_reminder_time": updated_preferences.weekly_weight_reminder_time
            }
        )
    except Exception as e:
        raise handle_exception(e)


@router.post(
    "/devices",
    response_model=DeviceTokenResponse,
    summary="Register device token",
    description="Register a device token for push notifications"
)
async def register_device_token(
    request: DeviceTokenRegisterRequest,
    user_id: str = Query(..., description="User ID"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Register device token for push notifications.
    
    Registers a new device or updates an existing one:
    - iOS devices with APNs token
    - Android devices with FCM token
    - Web devices with FCM token
    
    If device token already exists, updates the last_used_at timestamp.
    """
    try:
        # Create command
        command = RegisterDeviceTokenCommand(
            user_id=user_id,
            device_token=request.device_token,
            platform=request.platform,
            device_info=request.device_info
        )
        
        # Execute command
        device = await event_bus.send(command)
        
        # Return response
        return DeviceTokenResponse(
            device_id=device.id,
            user_id=device.user_id,
            platform=device.platform,
            is_active=device.is_active,
            last_used_at=device.last_used_at,
            created_at=device.created_at
        )
    except Exception as e:
        raise handle_exception(e)


@router.get(
    "/devices",
    response_model=DeviceListResponse,
    summary="List user devices",
    description="Get list of registered devices for user"
)
async def list_user_devices(
    user_id: str = Query(..., description="User ID"),
    active_only: bool = Query(True, description="Return only active devices"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    List user's registered devices.
    
    Returns all devices registered for push notifications:
    - iOS devices
    - Android devices
    - Web devices
    
    Can filter by active status.
    """
    try:
        # Create query
        query = GetUserDevicesQuery(
            user_id=user_id,
            active_only=active_only
        )
        
        # Execute query
        devices = await event_bus.send(query)
        
        # Convert to response
        device_responses = [
            DeviceTokenResponse(
                device_id=device.id,
                user_id=device.user_id,
                platform=device.platform,
                is_active=device.is_active,
                last_used_at=device.last_used_at,
                created_at=device.created_at
            )
            for device in devices
        ]
        
        return DeviceListResponse(
            devices=device_responses,
            total=len(device_responses)
        )
    except Exception as e:
        raise handle_exception(e)


@router.delete(
    "/devices/{device_id}",
    summary="Unregister device token",
    description="Remove a device token registration"
)
async def unregister_device_token(
    device_id: str,
    user_id: str = Query(..., description="User ID"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Unregister device token.
    
    Removes device from receiving push notifications:
    - Deactivates the device token
    - User can re-register the same device later
    """
    try:
        # Create command
        command = UnregisterDeviceTokenCommand(
            user_id=user_id,
            device_id=device_id
        )
        
        # Execute command
        await event_bus.send(command)
        
        return {"success": True, "message": "Device unregistered successfully"}
    except Exception as e:
        raise handle_exception(e)


@router.get(
    "/history",
    response_model=NotificationHistoryResponse,
    summary="Get notification history",
    description="Retrieve notification history for user"
)
async def get_notification_history(
    user_id: str = Query(..., description="User ID"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Get notification history.
    
    Returns paginated list of sent notifications:
    - Sent timestamp
    - Delivery status
    - Notification content
    - Can filter by notification type
    """
    try:
        # Create query
        query = GetNotificationHistoryQuery(
            user_id=user_id,
            notification_type=notification_type,
            limit=limit,
            offset=offset
        )
        
        # Execute query
        result = await event_bus.send(query)
        
        # Convert to response
        log_responses = [
            NotificationLogResponse(
                id=log.id,
                notification_type=log.notification_type,
                delivery_method=log.delivery_method,
                title=log.title,
                body=log.body,
                status=log.status,
                sent_at=log.sent_at,
                delivered_at=log.delivered_at,
                opened_at=log.opened_at,
                created_at=log.created_at
            )
            for log in result["logs"]
        ]
        
        return NotificationHistoryResponse(
            notifications=log_responses,
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"]
        )
    except Exception as e:
        raise handle_exception(e)


@router.post(
    "/test",
    response_model=TestNotificationResponse,
    summary="Send test notification",
    description="Send a test notification to user (for testing purposes)"
)
async def send_test_notification(
    request: TestNotificationRequest,
    user_id: str = Query(..., description="User ID"),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Send test notification.
    
    Sends a test notification to verify setup:
    - Tests push notification delivery
    - Tests email notification delivery
    - Returns delivery status and notification IDs
    """
    try:
        # Create command
        command = SendTestNotificationCommand(
            user_id=user_id,
            notification_type=request.notification_type,
            delivery_method=request.delivery_method
        )
        
        # Execute command
        result = await event_bus.send(command)
        
        return TestNotificationResponse(
            success=result["success"],
            message=result["message"],
            notification_ids=result["notification_ids"]
        )
    except Exception as e:
        raise handle_exception(e)
