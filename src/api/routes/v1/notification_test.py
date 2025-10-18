"""
Test endpoints for push notifications.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies.event_bus import get_configured_event_bus
from src.api.exceptions import handle_exception
from src.infra.event_bus import EventBus

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
    event_bus: EventBus = Depends(get_configured_event_bus)
):
    """
    Send a test notification to a user.
    
    This endpoint allows testing push notifications without waiting for scheduled times.
    """
    try:
        # This would need to be implemented as a command/query pattern
        # For now, we'll return a placeholder response
        
        return TestNotificationResponse(
            success=True,
            message=f"Test notification would be sent to user {request.user_id}",
            details={
                "user_id": request.user_id,
                "notification_type": request.notification_type,
                "note": "This is a placeholder - implement actual notification sending"
            }
        )
        
    except Exception as e:
        raise handle_exception(e)


@router.get("/status")
async def get_notification_status():
    """
    Get the status of the notification system.
    
    Returns information about the notification service status.
    """
    try:
        # This would check if Firebase is initialized and services are running
        return {
            "firebase_initialized": True,  # Placeholder
            "scheduled_service_running": True,  # Placeholder
            "message": "Notification system status check"
        }
        
    except Exception as e:
        raise handle_exception(e)
