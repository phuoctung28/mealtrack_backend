"""Handler for retrieving a user's saved suggestions."""
import logging
from typing import Any, Dict, List, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.saved_suggestion import GetSavedSuggestionsQuery
from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetSavedSuggestionsQuery)
class GetSavedSuggestionsQueryHandler(EventHandler[GetSavedSuggestionsQuery, Dict[str, Any]]):
    """Return all saved suggestions for a user, newest first."""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetSavedSuggestionsQuery) -> Dict[str, Any]:
        cache_key, ttl = CacheKeys.saved_suggestions(query.user_id)
        if self.cache_service:
            cached = await self.cache_service.get_json(cache_key)
            if cached is not None:
                return cached
        result = await self._compute(query)
        if self.cache_service:
            await self.cache_service.set_json(cache_key, result, ttl)
        return result

    async def _compute(self, query: GetSavedSuggestionsQuery) -> Dict[str, Any]:
        with UnitOfWork() as uow:
            rows = uow.saved_suggestions_db.find_by_user(query.user_id)
            items = [
                {
                    "id": row.id,
                    "suggestion_id": row.suggestion_id,
                    "meal_type": row.meal_type,
                    "portion_multiplier": row.portion_multiplier,
                    "suggestion_data": row.suggestion_data,
                    "saved_at": row.saved_at.isoformat() if row.saved_at else None,
                }
                for row in rows
            ]
            return {"items": items, "count": len(items)}
