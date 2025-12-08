"""
Handler for registering FCM tokens.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.app.commands.notification import RegisterFcmTokenCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.notification import UserFcmToken, DeviceType
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.services.timezone_utils import is_valid_timezone
from src.infra.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@handles(RegisterFcmTokenCommand)
class RegisterFcmTokenCommandHandler(
    EventHandler[RegisterFcmTokenCommand, Dict[str, Any]]
):
    """Handler for registering FCM tokens."""

    def __init__(
        self,
        notification_repository: NotificationRepositoryPort = None,
        db: Optional[Session] = None
    ):
        self.notification_repository = notification_repository
        self.db = db
        self.user_repository = UserRepository(db) if db else None

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        self.notification_repository = kwargs.get(
            "notification_repository", self.notification_repository
        )
        self.db = kwargs.get("db", self.db)
        if self.db:
            self.user_repository = UserRepository(self.db)

    async def handle(self, command: RegisterFcmTokenCommand) -> Dict[str, Any]:
        """Handle FCM token registration with old token cleanup."""
        if not self.notification_repository:
            raise RuntimeError("Notification repository not configured")

        try:
            device_type = (
                DeviceType.IOS if command.device_type == "ios" else DeviceType.ANDROID
            )

            # 1. Deactivate OLD tokens for this user+device (token refresh scenario)
            existing_tokens = (
                self.notification_repository.find_active_fcm_tokens_by_user(
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
                    self.notification_repository.deactivate_fcm_token(
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

            saved_token = self.notification_repository.save_fcm_token(fcm_token)

            # 3. Update user timezone if provided and valid
            if command.timezone and self.user_repository:
                if is_valid_timezone(command.timezone):
                    self.user_repository.update_user_timezone(command.user_id, command.timezone)
                    logger.info(f"Updated timezone for user {command.user_id}: {command.timezone}")
                else:
                    logger.warning(f"Invalid timezone from user {command.user_id}: {command.timezone}")

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
        except Exception as e:
            logger.error(f"Error registering FCM token: {e}")
            raise e
