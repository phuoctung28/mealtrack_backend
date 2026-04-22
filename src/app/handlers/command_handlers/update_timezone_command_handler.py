"""Handler for updating user timezone."""
import logging
from typing import Dict, Any

from src.app.commands.user.update_timezone_command import UpdateTimezoneCommand
from src.app.events.base import EventHandler, handles
from src.domain.utils.timezone_utils import is_valid_timezone, normalize_timezone
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(UpdateTimezoneCommand)
class UpdateTimezoneCommandHandler(EventHandler[UpdateTimezoneCommand, Dict[str, Any]]):
    """Handler for updating user timezone."""

    async def handle(self, command: UpdateTimezoneCommand) -> Dict[str, Any]:
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
                f"Timezone unchanged for user {command.user_id}: {canonical_tz!r} — skipping write"
            )
            return {"success": True, "timezone": canonical_tz}

        # Write: only open a UoW when we actually need to write
        async with AsyncUnitOfWork() as uow:
            await uow.users.update_user_timezone(command.user_id, canonical_tz)
            await uow.commit()

        logger.info(f"Updated timezone for user {command.user_id}: {canonical_tz}")
        return {"success": True, "timezone": canonical_tz}
