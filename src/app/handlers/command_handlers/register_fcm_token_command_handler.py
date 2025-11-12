"""
Handler for registering FCM tokens.
"""
import logging
from typing import Any, Dict

from src.app.commands.notification import RegisterFcmTokenCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.notification import UserFcmToken, DeviceType
from src.domain.ports.notification_repository_port import NotificationRepositoryPort

logger = logging.getLogger(__name__)


@handles(RegisterFcmTokenCommand)
class RegisterFcmTokenCommandHandler(EventHandler[RegisterFcmTokenCommand, Dict[str, Any]]):
    """Handler for registering FCM tokens."""
    
    def __init__(self, notification_repository: NotificationRepositoryPort = None):
        self.notification_repository = notification_repository
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.notification_repository = kwargs.get('notification_repository', self.notification_repository)
    
    async def handle(self, command: RegisterFcmTokenCommand) -> Dict[str, Any]:
        """Handle FCM token registration."""
        if not self.notification_repository:
            raise RuntimeError("Notification repository not configured")
        
        try:
            # Convert device type string to enum
            device_type = DeviceType.IOS if command.device_type == 'ios' else DeviceType.ANDROID
            
            # Create domain model
            fcm_token = UserFcmToken.create_new(
                user_id=command.user_id,
                fcm_token=command.fcm_token,
                device_type=device_type
            )
            
            # Save to repository
            saved_token = self.notification_repository.save_fcm_token(fcm_token)
            
            logger.info(f"FCM token registered for user {command.user_id}")
            
            return {
                "success": True,
                "message": "Token registered successfully",
                "token_id": saved_token.token_id
            }
        except Exception as e:
            logger.error(f"Error registering FCM token: {e}")
            raise e