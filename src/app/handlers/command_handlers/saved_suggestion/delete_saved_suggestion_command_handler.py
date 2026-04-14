"""Handler for deleting a saved suggestion."""
import logging
from typing import Any, Dict, Optional

from src.app.commands.saved_suggestion import DeleteSavedSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteSavedSuggestionCommand)
class DeleteSavedSuggestionCommandHandler(EventHandler[DeleteSavedSuggestionCommand, Dict[str, Any]]):
    """Delete a saved suggestion by suggestion_id for a user."""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, command: DeleteSavedSuggestionCommand) -> Dict[str, Any]:
        with UnitOfWork() as uow:
            deleted = uow.saved_suggestions_db.delete_by_user_and_suggestion(
                command.user_id, command.suggestion_id
            )
            if deleted:
                logger.info(f"Deleted saved suggestion {command.suggestion_id} for user {command.user_id}")

        if self.cache_service:
            cache_key, _ = CacheKeys.saved_suggestions(command.user_id)
            await self.cache_service.invalidate(cache_key)

        return {"success": deleted}
