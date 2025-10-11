"""
API routes for notification preferences and management.
"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.base_dependencies import get_db
from src.api.schemas.request.notification_requests import (
    NotificationPreferencesUpdateRequest,
    DeviceTokenRegisterRequest,
    TestNotificationRequest,
    AdminNotificationTriggerRequest
)
from src.api.schemas.response.notification_responses import (
    NotificationPreferencesResponse,
    DeviceTokenResponse,
    DeviceListResponse,
    NotificationHistoryResponse,
    TestNotificationResponse,
    AdminNotificationTriggerResponse,
    NotificationLogResponse
)
from src.app.services.notification_service_factory import NotificationServiceFactory
from src.app.services.notification_preference_service import NotificationPreferenceService
from src.infra.repositories.notification_repository import (
    DeviceTokenRepository,
    NotificationLogRepository
)
from src.domain.model.notification import Notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["notifications"])


# Dependency to get notification preference service
def get_preference_service(session: AsyncSession = Depends(get_db)) -> NotificationPreferenceService:
    """Get notification preference service"""
    return NotificationServiceFactory.create_preference_service(session)


# Dependency to get device token repository
def get_device_repository(session: AsyncSession = Depends(get_db)) -> DeviceTokenRepository:
    """Get device token repository"""
    return DeviceTokenRepository(session)


# Dependency to get notification log repository
def get_notification_repository(session: AsyncSession = Depends(get_db)) -> NotificationLogRepository:
    """Get notification log repository"""
    return NotificationLogRepository(session)


@router.get(
    "/users/{user_id}/preferences/notifications",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
    description="Retrieve user's notification preferences"
)
async def get_notification_preferences(
    user_id: str,
    service: NotificationPreferenceService = Depends(get_preference_service)
):
    """Get user notification preferences"""
    try:
        preferences = await service.get_preferences(user_id)
        
        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification preferences"
        )


@router.put(
    "/users/{user_id}/preferences/notifications",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
    description="Update user's notification preferences"
)
async def update_notification_preferences(
    user_id: str,
    request: NotificationPreferencesUpdateRequest,
    service: NotificationPreferenceService = Depends(get_preference_service)
):
    """Update user notification preferences"""
    try:
        updated_preferences = await service.update_preferences(
            user_id=user_id,
            notifications_enabled=request.notifications_enabled,
            push_notifications_enabled=request.push_notifications_enabled,
            email_notifications_enabled=request.email_notifications_enabled,
            weekly_weight_reminder_enabled=request.weekly_weight_reminder_enabled,
            weekly_weight_reminder_day=request.weekly_weight_reminder_day,
            weekly_weight_reminder_time=request.weekly_weight_reminder_time
        )
        
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
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences"
        )


@router.post(
    "/users/{user_id}/devices",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register device token",
    description="Register a device token for push notifications"
)
async def register_device_token(
    user_id: str,
    request: DeviceTokenRegisterRequest,
    repository: DeviceTokenRepository = Depends(get_device_repository)
):
    """Register device token"""
    try:
        # Check if device token already exists
        existing = await repository.get_by_token(request.device_token)
        if existing:
            # Update existing device
            await repository.update_last_used(existing.id)
            return DeviceTokenResponse(
                device_id=existing.id,
                user_id=existing.user_id,
                platform=existing.platform,
                is_active=existing.is_active,
                last_used_at=existing.last_used_at,
                created_at=existing.created_at
            )
        
        # Create new device token
        device = await repository.create(
            user_id=user_id,
            device_token=request.device_token,
            platform=request.platform,
            device_info=request.device_info
        )
        
        return DeviceTokenResponse(
            device_id=device.id,
            user_id=device.user_id,
            platform=device.platform,
            is_active=device.is_active,
            last_used_at=device.last_used_at,
            created_at=device.created_at
        )
    except Exception as e:
        logger.error(f"Error registering device token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device token"
        )


@router.get(
    "/users/{user_id}/devices",
    response_model=DeviceListResponse,
    summary="List user devices",
    description="Get list of registered devices for user"
)
async def list_user_devices(
    user_id: str,
    active_only: bool = Query(True, description="Return only active devices"),
    repository: DeviceTokenRepository = Depends(get_device_repository)
):
    """List user devices"""
    try:
        devices = await repository.get_all_user_devices(user_id, active_only)
        
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
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve devices"
        )


@router.delete(
    "/users/{user_id}/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister device token",
    description="Remove a device token registration"
)
async def unregister_device_token(
    user_id: str,
    device_id: str,
    repository: DeviceTokenRepository = Depends(get_device_repository)
):
    """Unregister device token"""
    try:
        # Verify device belongs to user
        device = await repository.get_by_id(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        if device.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device does not belong to user"
            )
        
        # Delete device
        deleted = await repository.delete_by_id(device_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister device"
        )


@router.get(
    "/users/{user_id}/notifications/history",
    response_model=NotificationHistoryResponse,
    summary="Get notification history",
    description="Retrieve notification history for user"
)
async def get_notification_history(
    user_id: str,
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    repository: NotificationLogRepository = Depends(get_notification_repository)
):
    """Get notification history"""
    try:
        logs, total = await repository.get_user_logs(
            user_id=user_id,
            notification_type=notification_type,
            limit=limit,
            offset=offset
        )
        
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
            for log in logs
        ]
        
        return NotificationHistoryResponse(
            notifications=log_responses,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification history"
        )


@router.post(
    "/users/{user_id}/notifications/test",
    response_model=TestNotificationResponse,
    summary="Send test notification",
    description="Send a test notification to user (for testing purposes)"
)
async def send_test_notification(
    user_id: str,
    request: TestNotificationRequest,
    session: AsyncSession = Depends(get_db)
):
    """Send test notification"""
    try:
        # Initialize services with proper configuration
        push_service = NotificationServiceFactory.create_push_service(session)
        
        # Create test notification
        notification = Notification(
            user_id=user_id,
            notification_type=request.notification_type,
            delivery_method=request.delivery_method,
            title="Test Notification",
            body="This is a test notification from Nutree AI",
            data={"test": True}
        )
        
        # Send notification
        notification_ids = await push_service.send_push_notification(user_id, notification)
        
        return TestNotificationResponse(
            success=len(notification_ids) > 0,
            message="Test notification sent successfully" if notification_ids else "No devices found",
            notification_ids=notification_ids
        )
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )

