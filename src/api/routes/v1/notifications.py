"""
Notifications API endpoints for push notification management.
"""
from fastapi import APIRouter, Depends

from src.api.dependencies.auth import get_current_user_id
from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.api.schemas.request.notification_requests import (
    FcmTokenRegistrationRequest,
    FcmTokenDeletionRequest,
    NotificationPreferencesUpdateRequest
)
from src.api.schemas.response.notification_responses import (
    FcmTokenResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateResponse
)
from src.app.commands.notification import (
    RegisterFcmTokenCommand,
    DeleteFcmTokenCommand,
    UpdateNotificationPreferencesCommand
)
from src.app.queries.notification import GetNotificationPreferencesQuery
from src.infra.event_bus import EventBus

router = APIRouter(prefix="/v1/notifications", tags=["Notifications"])


@router.post("/tokens", response_model=FcmTokenResponse)
async def register_fcm_token(
    request: FcmTokenRegistrationRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Register an FCM token for push notifications.
    
    This endpoint allows mobile apps to register their FCM tokens
    for receiving push notifications.
    """
    try:
        command = RegisterFcmTokenCommand(
            user_id=user_id,
            fcm_token=request.fcm_token,
            device_type=request.device_type
        )
        
        result = await event_bus.send(command)
        
        return FcmTokenResponse(
            success=result["success"],
            message=result["message"]
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.delete("/tokens", response_model=FcmTokenResponse)
async def delete_fcm_token(
    request: FcmTokenDeletionRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    # Get user_id from dev auth bypass
    """
    Delete an FCM token (used during logout).
    
    This endpoint allows mobile apps to unregister their FCM tokens
    when users log out.
    """
    try:
        command = DeleteFcmTokenCommand(
            user_id=user_id,
            fcm_token=request.fcm_token
        )
        
        result = await event_bus.send(command)
        
        return FcmTokenResponse(
            success=result["success"],
            message=result["message"]
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    # Get user_id from dev auth bypass
    """
    Get user's notification preferences.
    
    Returns the current notification preferences for the user.
    If no preferences exist, creates and returns default preferences.
    """
    try:
        query = GetNotificationPreferencesQuery(user_id=user_id)
        
        result = await event_bus.send(query)
        
        return NotificationPreferencesResponse(**result)
        
    except Exception as e:
        raise handle_exception(e)


@router.put("/preferences", response_model=NotificationPreferencesUpdateResponse)
async def update_notification_preferences(
    request: NotificationPreferencesUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Update user's notification preferences.
    
    Updates the notification preferences for the user.
    Only provided fields will be updated.
    """
    try:
        command = UpdateNotificationPreferencesCommand(
            user_id=user_id,
            meal_reminders_enabled=request.meal_reminders_enabled,
            water_reminders_enabled=request.water_reminders_enabled,
            sleep_reminders_enabled=request.sleep_reminders_enabled,
            progress_notifications_enabled=request.progress_notifications_enabled,
            reengagement_notifications_enabled=request.reengagement_notifications_enabled,
            breakfast_time_minutes=request.breakfast_time_minutes,
            lunch_time_minutes=request.lunch_time_minutes,
            dinner_time_minutes=request.dinner_time_minutes,
            water_reminder_interval_hours=request.water_reminder_interval_hours,
            sleep_reminder_time_minutes=request.sleep_reminder_time_minutes,
        )
        
        result = await event_bus.send(command)
        
        return NotificationPreferencesUpdateResponse(
            success=result["success"],
            preferences=NotificationPreferencesResponse(**result["preferences"])
        )
        
    except Exception as e:
        raise handle_exception(e)
