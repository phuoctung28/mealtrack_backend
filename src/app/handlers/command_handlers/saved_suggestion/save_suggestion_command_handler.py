"""Handler for saving a meal suggestion to user's bookmarks."""
import logging
from typing import Any, Dict, Optional

from src.app.commands.saved_suggestion import SaveSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort
from src.domain.ports.unit_of_work_port import UnitOfWorkPort

logger = logging.getLogger(__name__)


@handles(SaveSuggestionCommand)
class SaveSuggestionCommandHandler(EventHandler[SaveSuggestionCommand, Dict[str, Any]]):
    """Save a meal suggestion. Returns existing if already saved (idempotent)."""

    def __init__(self, uow: UnitOfWorkPort, cache_service: Optional[CachePort] = None):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: SaveSuggestionCommand) -> Dict[str, Any]:
        async with self.uow as uow:
            # Check if already saved (idempotent)
            existing = await uow.saved_suggestions.find_by_user_and_suggestion(
                command.user_id, command.suggestion_id
            )
            if existing:
                return existing

            result = await uow.saved_suggestions.save(
                user_id=command.user_id,
                suggestion_id=command.suggestion_id,
                meal_type=command.meal_type,
                portion_multiplier=command.portion_multiplier,
                suggestion_data=command.suggestion_data,
            )
            logger.info(f"Saved suggestion {command.suggestion_id} for user {command.user_id}")

        if self.cache_service:
            cache_key, _ = CacheKeys.saved_suggestions(command.user_id)
            await self.cache_service.invalidate(cache_key)

        return result
