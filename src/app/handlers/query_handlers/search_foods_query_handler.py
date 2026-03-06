"""
SearchFoodsQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Any, Dict, List, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.food.search_foods_query import SearchFoodsQuery
from src.domain.services.food_mapping_service import FoodMappingService

logger = logging.getLogger(__name__)


@handles(SearchFoodsQuery)
class SearchFoodsQueryHandler(EventHandler[SearchFoodsQuery, Dict[str, Any]]):
    """Handler for searching foods in the database."""

    def __init__(
        self,
        cache_service,
        mapping_service: FoodMappingService,
        fat_secret_service: Optional[Any] = None,
    ):
        self.cache_service = cache_service
        self.mapping_service = mapping_service
        self.fat_secret_service = fat_secret_service

    async def handle(self, event: SearchFoodsQuery) -> Dict[str, Any]:
        if not event.query or not event.query.strip():
            return {"results": [], "query": event.query, "total": 0}

        cached = await self.cache_service.get_cached_search(event.query)
        if cached is not None:
            processed_cached = self._process_search_results(cached)
            for item in processed_cached:
                if "source" not in item:
                    item["source"] = "fatsecret"
            mapped = [self.mapping_service.map_search_item(i) for i in processed_cached]
            return {"results": mapped, "query": event.query, "total": len(mapped)}

        # FatSecret only
        processed_raw = []

        if self.fat_secret_service:
            try:
                fs_results = await self.fat_secret_service.search_foods(event.query, max_results=event.limit)
                processed_raw.extend(fs_results)
            except Exception:
                logger.warning("FatSecret search failed", exc_info=True)

        await self.cache_service.cache_search(event.query, processed_raw)
        mapped = [self.mapping_service.map_search_item(i) for i in processed_raw]
        return {"results": mapped, "query": event.query, "total": len(mapped)}

    def _process_search_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process search results: deduplicate and capitalize names."""
        if not raw_results:
            return raw_results

        seen_names = set()
        processed_results = []

        for item in raw_results:
            original_name = item.get("description", "")
            capitalized_name = self._capitalize_food_name(original_name)
            name_key = capitalized_name.lower().strip()

            if name_key not in seen_names:
                seen_names.add(name_key)
                processed_item = item.copy()
                processed_item["description"] = capitalized_name
                processed_results.append(processed_item)

        return processed_results

    def _capitalize_food_name(self, name: str) -> str:
        """Properly capitalize food names."""
        if not name:
            return name

        parts = []
        for part in name.split(','):
            words = []
            for word in part.strip().split():
                word_lower = word.lower()
                if word_lower in ['and', 'or', 'with', 'in', 'on', 'of', 'the', 'a', 'an']:
                    words.append(word_lower if words else word.capitalize())
                else:
                    words.append(word.capitalize())

            if words:
                parts.append(' '.join(words))

        return ', '.join(parts)
