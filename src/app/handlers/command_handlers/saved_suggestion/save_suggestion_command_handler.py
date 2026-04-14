"""Handler for saving a meal suggestion to user's bookmarks."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.app.commands.saved_suggestion import SaveSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.models.saved_suggestion import SavedSuggestionModel
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(SaveSuggestionCommand)
class SaveSuggestionCommandHandler(EventHandler[SaveSuggestionCommand, Dict[str, Any]]):
    """Save a meal suggestion. Returns existing if already saved (idempotent)."""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, command: SaveSuggestionCommand) -> Dict[str, Any]:
        with UnitOfWork() as uow:
            # Check if already saved (idempotent)
            existing = uow.saved_suggestions_db.find_by_user_and_suggestion(
                command.user_id, command.suggestion_id
            )
            if existing:
                return self._to_response(existing)

            now = datetime.now(timezone.utc)
            model = SavedSuggestionModel(
                user_id=command.user_id,
                suggestion_id=command.suggestion_id,
                meal_type=command.meal_type,
                portion_multiplier=command.portion_multiplier,
                suggestion_data=command.suggestion_data,
                saved_at=now,
                created_at=now,
            )
            saved = uow.saved_suggestions_db.create(model)
            logger.info(f"Saved suggestion {command.suggestion_id} for user {command.user_id}")
            result = self._to_response(saved)

        if self.cache_service:
            cache_key, _ = CacheKeys.saved_suggestions(command.user_id)
            await self.cache_service.invalidate(cache_key)

        return result

    def _to_response(self, model: SavedSuggestionModel) -> Dict[str, Any]:
        return {
            "id": model.id,
            "suggestion_id": model.suggestion_id,
            "meal_type": model.meal_type,
            "portion_multiplier": model.portion_multiplier,
            "suggestion_data": model.suggestion_data,
            "saved_at": model.saved_at.isoformat() if model.saved_at else None,
        }
