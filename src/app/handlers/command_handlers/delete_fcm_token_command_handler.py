"""
Handler for deleting FCM tokens.
"""
import logging
from typing import Any, Dict

from src.app.commands.notification import DeleteFcmTokenCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteFcmTokenCommand)
class DeleteFcmTokenCommandHandler(EventHandler[DeleteFcmTokenCommand, Dict[str, Any]]):
    """Handler for deleting FCM tokens."""

    def __init__(self):
        pass

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        pass

    async def handle(self, command: DeleteFcmTokenCommand) -> Dict[str, Any]:
        """Handle FCM token deletion."""
        try:
            with UnitOfWork() as uow:
                existing_token = uow.notifications.find_fcm_token_by_token(command.fcm_token)

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

                deleted = uow.notifications.delete_fcm_token(command.fcm_token)
                uow.commit()

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
