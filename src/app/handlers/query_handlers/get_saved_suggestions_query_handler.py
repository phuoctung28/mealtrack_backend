"""Handler for retrieving a user's saved suggestions."""
import logging
from typing import Any, Dict, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.saved_suggestion import GetSavedSuggestionsQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(GetSavedSuggestionsQuery)
class GetSavedSuggestionsQueryHandler(EventHandler[GetSavedSuggestionsQuery, Dict[str, Any]]):
    """Return all saved suggestions for a user, newest first."""

    def __init__(self, cache_service: Optional[CachePort] = None):
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
        async with AsyncUnitOfWork() as uow:
            rows = await uow.saved_suggestions_db.find_by_user(query.user_id)
            return {"items": rows, "count": len(rows)}
