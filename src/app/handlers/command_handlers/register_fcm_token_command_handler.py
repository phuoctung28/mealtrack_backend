"""
Handler for registering FCM tokens.
"""

import inspect
import logging
from typing import Any

from src.app.commands.notification import RegisterFcmTokenCommand
from src.app.events.base import EventHandler, handles
from src.app.services.background_job_scheduler import schedule_background_job
from src.domain.model.notification import DeviceType, UserFcmToken
from src.domain.ports.notification_repository_port import NotificationRepositoryPort
from src.domain.utils.timezone_utils import is_valid_timezone, normalize_timezone
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)

logger = logging.getLogger(__name__)


@handles(RegisterFcmTokenCommand)
class RegisterFcmTokenCommandHandler(
    EventHandler[RegisterFcmTokenCommand, dict[str, Any]]
):
    """Handler for registering FCM tokens."""

    def __init__(
        self,
        notification_repository: NotificationRepositoryPort = None,
        precompute_service: DailyContextPrecomputeService | None = None,
        task_manager=None,
    ):
        self.notification_repository = notification_repository
        self.precompute_service = precompute_service
        self.task_manager = task_manager

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if "precompute_service" in kwargs:
            self.precompute_service = kwargs["precompute_service"]
        if "task_manager" in kwargs:
            self.task_manager = kwargs["task_manager"]

    async def handle(self, command: RegisterFcmTokenCommand) -> dict[str, Any]:
        """Handle FCM token registration with old token cleanup."""
        timezone_changed = False
        durable_reschedule_queued = False
        async with AsyncUnitOfWork() as uow:
            # Use notification repository from UoW if not injected
            notification_repo = self.notification_repository or uow.notifications

            device_type = (
                DeviceType.IOS if command.device_type == "ios" else DeviceType.ANDROID
            )

            # 1. Deactivate OLD tokens for this user+device (token refresh scenario)
            existing_tokens = await notification_repo.find_active_fcm_tokens_by_user(
                command.user_id
            )
            deactivated_count = 0
            for old_token in existing_tokens:
                # Deactivate tokens of same device type (new token replaces old)
                if (
                    old_token.device_type == device_type
                    and old_token.fcm_token != command.fcm_token
                ):
                    await notification_repo.deactivate_fcm_token(old_token.fcm_token)
                    deactivated_count += 1
                    logger.info(f"Deactivated old FCM token for user {command.user_id}")

            # 2. Create/update new token
            fcm_token = UserFcmToken.create_new(
                user_id=command.user_id,
                fcm_token=command.fcm_token,
                device_type=device_type,
            )

            saved_token = await notification_repo.save_fcm_token(fcm_token)

            # 3. Update user timezone if provided
            if command.timezone and is_valid_timezone(command.timezone):
                canonical_tz = normalize_timezone(command.timezone)
                current_tz = await uow.users.get_user_timezone(command.user_id)
                if current_tz != canonical_tz:
                    await uow.users.update_user_timezone(command.user_id, canonical_tz)
                    timezone_changed = True
                    logger.info(
                        f"Updated timezone for user {command.user_id}: {canonical_tz}"
                    )
            elif command.timezone:
                logger.warning(
                    "Invalid timezone ignored during FCM registration: %r for user %s",
                    command.timezone,
                    command.user_id,
                )

            if timezone_changed:
                outbox = getattr(uow, "outbox", None)
                if outbox is not None and inspect.iscoroutinefunction(
                    getattr(outbox, "enqueue", None)
                ):
                    await outbox.enqueue(
                        "notification_reschedule",
                        {"user_id": command.user_id, "reason": "fcm_timezone"},
                        event_id=(
                            f"notification-reschedule:fcm-timezone:{command.user_id}:"
                            f"{command.timezone}"
                        ),
                        aggregate_type="user",
                        aggregate_id=command.user_id,
                    )
                    durable_reschedule_queued = True

            # UoW auto-commits on exit

        if timezone_changed and not durable_reschedule_queued:
            self._schedule_notification_reschedule(command.user_id, "fcm_timezone")

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

    def _schedule_notification_reschedule(self, user_id: str, reason: str) -> None:
        if self.precompute_service is None:
            return
        schedule_background_job(
            self.task_manager,
            f"notifications:reschedule:{user_id}:{reason}",
            self.precompute_service.reschedule_user_notifications(user_id),
            logger=logger,
        )
