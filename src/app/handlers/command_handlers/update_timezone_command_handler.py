"""Handler for updating user timezone."""
import logging
from typing import Dict, Any

from src.app.commands.user.update_timezone_command import UpdateTimezoneCommand
from src.app.events.base import EventHandler, handles
from src.domain.utils.timezone_utils import is_valid_timezone
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(UpdateTimezoneCommand)
class UpdateTimezoneCommandHandler(EventHandler[UpdateTimezoneCommand, Dict[str, Any]]):
    """Handler for updating user timezone."""

    async def handle(self, command: UpdateTimezoneCommand) -> Dict[str, Any]:
        """Handle timezone update command."""
        if not is_valid_timezone(command.timezone):
            return {"success": False, "error": "Invalid timezone"}

        with UnitOfWork() as uow:
            uow.users.update_user_timezone(command.user_id, command.timezone)
            uow.commit()

        logger.info(f"Updated timezone for user {command.user_id}: {command.timezone}")
        return {"success": True, "timezone": command.timezone}
