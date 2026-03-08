"""Handler for deleting a saved suggestion."""
import logging
from typing import Any, Dict

from src.app.commands.saved_suggestion import DeleteSavedSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteSavedSuggestionCommand)
class DeleteSavedSuggestionCommandHandler(EventHandler[DeleteSavedSuggestionCommand, Dict[str, Any]]):
    """Delete a saved suggestion by suggestion_id for a user."""

    async def handle(self, command: DeleteSavedSuggestionCommand) -> Dict[str, Any]:
        with UnitOfWork() as uow:
            deleted = uow.saved_suggestions_db.delete_by_user_and_suggestion(
                command.user_id, command.suggestion_id
            )
            if deleted:
                logger.info(f"Deleted saved suggestion {command.suggestion_id} for user {command.user_id}")
            return {"success": deleted}
