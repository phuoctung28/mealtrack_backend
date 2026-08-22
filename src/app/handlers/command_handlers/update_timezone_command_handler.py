"""Handler for updating user timezone."""

import inspect
import logging
from typing import Any

from src.app.commands.user.update_timezone_command import UpdateTimezoneCommand
from src.app.events.base import EventHandler, handles
from src.app.services.background_job_scheduler import schedule_background_job
from src.domain.utils.timezone_utils import is_valid_timezone, normalize_timezone
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)

logger = logging.getLogger(__name__)


@handles(UpdateTimezoneCommand)
class UpdateTimezoneCommandHandler(EventHandler[UpdateTimezoneCommand, dict[str, Any]]):
    """Handler for updating user timezone."""

    def __init__(
        self,
        precompute_service: DailyContextPrecomputeService | None = None,
        task_manager=None,
    ):
        self.precompute_service = precompute_service
        self.task_manager = task_manager

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if "precompute_service" in kwargs:
            self.precompute_service = kwargs["precompute_service"]
        if "task_manager" in kwargs:
            self.task_manager = kwargs["task_manager"]

    async def handle(self, command: UpdateTimezoneCommand) -> dict[str, Any]:
        """Handle timezone update command. Skips DB write if timezone is unchanged."""
        logger.info(
            f"Timezone update request: user={command.user_id}, "
            f"timezone={command.timezone!r}"
        )
        if not is_valid_timezone(command.timezone):
            logger.warning(
                f"Invalid timezone rejected: {command.timezone!r} "
                f"for user {command.user_id}"
            )
            return {"success": False, "error": "Invalid timezone"}

        canonical_tz = normalize_timezone(command.timezone)

        # Read: open a UoW just to check the current timezone
        async with AsyncUnitOfWork() as uow:
            current_tz = await uow.users.get_user_timezone(command.user_id)

        if current_tz == canonical_tz:
            logger.debug(
                "Timezone unchanged for user %s: %r - skipping write",
                command.user_id,
                canonical_tz,
            )
            return {"success": True, "timezone": canonical_tz}

        # Write: only open a UoW when we actually need to write
        async with AsyncUnitOfWork() as uow:
            await uow.users.update_user_timezone(command.user_id, canonical_tz)
            outbox = getattr(uow, "outbox", None)
            if outbox is not None and inspect.iscoroutinefunction(
                getattr(outbox, "enqueue", None)
            ):
                await outbox.enqueue(
                    "notification_reschedule",
                    {"user_id": str(command.user_id), "reason": "timezone"},
                    event_id=(
                        f"notification-reschedule:timezone:{command.user_id}:"
                        f"{canonical_tz}"
                    ),
                    aggregate_type="user",
                    aggregate_id=str(command.user_id),
                )
            await uow.commit()

        logger.info(f"Updated timezone for user {command.user_id}: {canonical_tz}")

        self._schedule_notification_reschedule(str(command.user_id), "timezone")

        return {"success": True, "timezone": canonical_tz}

    def _schedule_notification_reschedule(self, user_id: str, reason: str) -> None:
        if self.precompute_service is None:
            return
        schedule_background_job(
            self.task_manager,
            f"notifications:reschedule:{user_id}:{reason}",
            self.precompute_service.reschedule_user_notifications(user_id),
            logger=logger,
        )
