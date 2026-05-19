"""Handler for updating user timezone."""

import logging
from typing import Any

from src.app.commands.user.update_timezone_command import UpdateTimezoneCommand
from src.app.events.base import EventHandler, handles
from src.domain.utils.timezone_utils import is_valid_timezone, normalize_timezone
from src.infra.database.uow_async import AsyncUnitOfWork
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)

logger = logging.getLogger(__name__)


@handles(UpdateTimezoneCommand)
class UpdateTimezoneCommandHandler(EventHandler[UpdateTimezoneCommand, dict[str, Any]]):
    """Handler for updating user timezone."""

    def __init__(self, precompute_service: DailyContextPrecomputeService | None = None):
        self.precompute_service = precompute_service

    def set_dependencies(self, **kwargs):
        """Set dependencies for dependency injection."""
        if "precompute_service" in kwargs:
            self.precompute_service = kwargs["precompute_service"]

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
            await uow.commit()

        logger.info(f"Updated timezone for user {command.user_id}: {canonical_tz}")

        if self.precompute_service:
            try:
                scheduled_count = (
                    await self.precompute_service.reschedule_user_notifications(
                        str(command.user_id)
                    )
                )
                logger.info(
                    "Rescheduled %s notifications after timezone update for user %s",
                    scheduled_count,
                    command.user_id,
                )
            except Exception as exc:
                logger.error(
                    "Failed to reschedule notifications after timezone update: %s",
                    exc,
                )

        return {"success": True, "timezone": canonical_tz}
