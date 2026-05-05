"""Handler for updating user language preference."""

import logging
from typing import Dict, Any

from src.app.commands.user.update_language_command import (
    UpdateLanguageCommand,
    SUPPORTED_LANGUAGES,
)
from src.app.events.base import EventHandler, handles
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(UpdateLanguageCommand)
class UpdateLanguageCommandHandler(EventHandler[UpdateLanguageCommand, Dict[str, Any]]):
    """Handler for updating user language preference."""

    async def handle(self, command: UpdateLanguageCommand) -> Dict[str, Any]:
        """Handle language update command."""
        language = command.language_code.lower().strip()

        if language not in SUPPORTED_LANGUAGES:
            logger.warning(
                f"Invalid language rejected: {language!r} for user {command.user_id}"
            )
            return {"success": False, "error": f"Unsupported language: {language}"}

        async with AsyncUnitOfWork() as uow:
            await uow.users.update_user_language(command.user_id, language)
            await uow.commit()

        logger.info(f"Updated language for user {command.user_id}: {language}")
        return {"success": True, "language_code": language}
