"""
Handler for registering FCM tokens.
"""

import logging
from typing import Any, Dict

from src.app.commands.notification import RegisterFcmTokenCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.notification import UserFcmToken, DeviceType
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.utils.timezone_utils import is_valid_timezone
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(RegisterFcmTokenCommand)
class RegisterFcmTokenCommandHandler(
    EventHandler[RegisterFcmTokenCommand, Dict[str, Any]]
):
    """Handler for registering FCM tokens."""

    def __init__(
        self,
        notification_repository: NotificationRepositoryPort = None
    ):
        self.notification_repository = notification_repository

    async def handle(self, command: RegisterFcmTokenCommand) -> Dict[str, Any]:
        """Handle FCM token registration with old token cleanup."""
        with UnitOfWork() as uow:
            # Use notification repository from UoW if not injected
            notification_repo = self.notification_repository or uow.notifications

            device_type = (
                DeviceType.IOS if command.device_type == "ios" else DeviceType.ANDROID
            )

            # 1. Deactivate OLD tokens for this user+device (token refresh scenario)
            existing_tokens = (
                notification_repo.find_active_fcm_tokens_by_user(
                    command.user_id
                )
            )
            deactivated_count = 0
            for old_token in existing_tokens:
                # Deactivate tokens of same device type (new token replaces old)
                if (
                    old_token.device_type == device_type
                    and old_token.fcm_token != command.fcm_token
                ):
                    notification_repo.deactivate_fcm_token(
                        old_token.fcm_token
                    )
                    deactivated_count += 1
                    logger.info(f"Deactivated old FCM token for user {command.user_id}")

            # 2. Create/update new token
            fcm_token = UserFcmToken.create_new(
                user_id=command.user_id,
                fcm_token=command.fcm_token,
                device_type=device_type,
            )

            saved_token = notification_repo.save_fcm_token(fcm_token)

            # 3. Update user timezone if provided and valid
            if command.timezone:
                if is_valid_timezone(command.timezone):
                    uow.users.update_user_timezone(command.user_id, command.timezone)
                    logger.info(f"Updated timezone for user {command.user_id}: {command.timezone}")
                else:
                    logger.warning(f"Invalid timezone from user {command.user_id}: {command.timezone}")

            # UoW auto-commits on exit
            
        logger.info(
            f"FCM token registered for user {command.user_id}, "
            f"deactivated {deactivated_count} old tokens"
        )

        return {
            "success": True,
            "message": "Token registered successfully",
            "token_id": saved_token.token_id,
            "deactivated_old_tokens": deactivated_count,
        }
