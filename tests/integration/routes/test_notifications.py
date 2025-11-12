"""
Test endpoints for push notifications.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.base_dependencies import (
    get_scheduled_notification_service,
    get_firebase_service
)
from src.api.exceptions import handle_exception

router = APIRouter(prefix="/v1/notification-test", tags=["Notification Testing"])


class TestNotificationRequest(BaseModel):
    """Request to send a test notification."""
    user_id: str = Field(..., description="User ID to send test notification to")
    notification_type: str = Field(default="test", description="Type of test notification")


class TestNotificationResponse(BaseModel):
    """Response for test notification."""
    success: bool = Field(..., description="Whether the notification was sent successfully")
    message: str = Field(..., description="Response message")
    details: dict = Field(default_factory=dict, description="Additional details")


@router.post("/send-test", response_model=TestNotificationResponse)
async def send_test_notification(
    request: TestNotificationRequest,
    scheduled_service = Depends(get_scheduled_notification_service)
):
    """
    Send a test notification to a user.
    
    This endpoint allows testing push notifications without waiting for scheduled times.
    """
    try:
        if not scheduled_service:
            raise HTTPException(
                status_code=503,
                detail="Scheduled notification service is not initialized"
            )
        
        # Send test notification using the scheduled notification service
        result = await scheduled_service.send_test_notification(
            user_id=request.user_id,
            notification_type=request.notification_type
        )
        
        if result.get("success"):
            return TestNotificationResponse(
                success=True,
                message=f"Test notification sent successfully to user {request.user_id}",
                details=result
            )
        else:
            return TestNotificationResponse(
                success=False,
                message=f"Failed to send test notification: {result.get('reason', 'unknown')}",
                details=result
            )
        
    except Exception as e:
        raise handle_exception(e) from e


@router.get("/status")
async def get_notification_status(
    scheduled_service = Depends(get_scheduled_notification_service),
    firebase_service = Depends(get_firebase_service)
):
    """
    Get the status of the notification system.
    
    Returns information about the notification service status.
    """
    try:
        firebase_initialized = firebase_service.is_initialized() if firebase_service else False
        scheduled_service_running = scheduled_service.is_running() if scheduled_service else False
        
        return {
            "firebase_initialized": firebase_initialized,
            "scheduled_service_running": scheduled_service_running,
            "scheduled_service_exists": scheduled_service is not None,
            "message": "Notification system is " + ("running" if scheduled_service_running else "not running"),
            "status": "healthy" if (firebase_initialized and scheduled_service_running) else "degraded"
        }
        
    except Exception as e:
        raise handle_exception(e) from e
