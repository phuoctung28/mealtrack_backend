"""
Handler for deleting FCM tokens.
"""
import logging
from typing import Any, Dict

from src.app.commands.notification import DeleteFcmTokenCommand
from src.app.events.base import EventHandler, handles
from src.domain.ports.notification_repository_port import NotificationRepositoryPort

logger = logging.getLogger(__name__)


@handles(DeleteFcmTokenCommand)
class DeleteFcmTokenCommandHandler(EventHandler[DeleteFcmTokenCommand, Dict[str, Any]]):
    """Handler for deleting FCM tokens."""
    
    def __init__(self, notification_repository: NotificationRepositoryPort = None):
        self.notification_repository = notification_repository
    
    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.notification_repository = kwargs.get('notification_repository', self.notification_repository)
    
    async def handle(self, command: DeleteFcmTokenCommand) -> Dict[str, Any]:
        """Handle FCM token deletion."""
        if not self.notification_repository:
            raise RuntimeError("Notification repository not configured")
        
        try:
            # Check if token exists and belongs to user
            existing_token = self.notification_repository.find_fcm_token_by_token(command.fcm_token)
            
            if not existing_token:
                return {
                    "success": False,
                    "message": "Token not found"
                }
            
            if existing_token.user_id != command.user_id:
                return {
                    "success": False,
                    "message": "Token does not belong to user"
                }
            
            # Delete token
            deleted = self.notification_repository.delete_fcm_token(command.fcm_token)
            
            if deleted:
                logger.info(f"FCM token deleted for user {command.user_id}")
                return {
                    "success": True,
                    "message": "Token deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to delete token"
                }
        except Exception as e:
            logger.error(f"Error deleting FCM token: {e}")
            raise e