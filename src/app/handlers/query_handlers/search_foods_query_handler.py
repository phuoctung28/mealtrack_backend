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
        translation_service: Optional[Any] = None,
    ):
        self.cache_service = cache_service
        self.mapping_service = mapping_service
        self.fat_secret_service = fat_secret_service
        self.translation_service = translation_service

    async def handle(self, event: SearchFoodsQuery) -> Dict[str, Any]:
        if not event.query or not event.query.strip():
            return {"results": [], "query": event.query, "total": 0}

        language = event.language
        is_non_english = language != "en"

        # Language-aware cache key (prefixed to avoid collisions)
        cache_key = f"{language}:{event.query}" if is_non_english else event.query
        cached = await self.cache_service.get_cached_search(cache_key)
        if cached is not None:
            processed_cached = self._process_search_results(cached)
            for item in processed_cached:
                if "source" not in item:
                    item["source"] = "fatsecret"
            mapped = [self.mapping_service.map_search_item(i) for i in processed_cached]
            return {"results": mapped, "query": event.query, "total": len(mapped)}

        processed_raw = []

        if self.fat_secret_service:
            if is_non_english:
                processed_raw = await self._search_localized(
                    event.query, event.limit, language, cache_key
                )
            else:
                try:
                    fs_results = await self.fat_secret_service.search_foods(
                        event.query, max_results=event.limit
                    )
                    processed_raw.extend(fs_results)
                    if processed_raw:
                        await self.cache_service.cache_search(cache_key, processed_raw)
                except Exception:
                    logger.warning("FatSecret search failed", exc_info=True)

        mapped = [self.mapping_service.map_search_item(i) for i in processed_raw]
        return {"results": mapped, "query": event.query, "total": len(mapped)}

    async def _search_localized(
        self, query: str, limit: int, language: str, cache_key: str
    ) -> List[Dict[str, Any]]:
        """Search with localization: try native region first, fallback only if empty."""
        from src.infra.adapters.fat_secret_service import LANGUAGE_TO_REGION

        region = LANGUAGE_TO_REGION.get(language, "US")

        # Step 1: Try FatSecret with localized region — cache and return immediately if anything found
        try:
            results = await self.fat_secret_service.search_foods(
                query,
                max_results=limit,
                region=region,
                language=language,
            )
            if results:
                logger.debug(
                    f"FatSecret region={region} returned {len(results)} results"
                )
                await self.cache_service.cache_search(cache_key, results)
                return results
        except Exception:
            logger.warning(f"FatSecret region={region} failed", exc_info=True)

        # Step 2: Translation fallback — only on true empty response from localized search
        if not self.translation_service:
            try:
                results = await self.fat_secret_service.search_foods(
                    query, max_results=limit
                )
                if results:
                    await self.cache_service.cache_search(cache_key, results)
                return results
            except Exception:
                return []

        translated_query = await self.translation_service.translate_query(
            query, language
        )
        if not translated_query:
            translated_query = query

        logger.info(f"Translation fallback: '{query}' -> '{translated_query}'")

        try:
            results = await self.fat_secret_service.search_foods(
                translated_query, max_results=limit
            )
        except Exception:
            logger.warning("FatSecret EN fallback failed", exc_info=True)
            return []

        if not results:
            return []

        results = await self.translation_service.translate_food_names(results, language)
        await self.cache_service.cache_search(cache_key, results)
        return results

    def _process_search_results(
        self, raw_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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
        for part in name.split(","):
            words = []
            for word in part.strip().split():
                word_lower = word.lower()
                if word_lower in [
                    "and",
                    "or",
                    "with",
                    "in",
                    "on",
                    "of",
                    "the",
                    "a",
                    "an",
                ]:
                    words.append(word_lower if words else word.capitalize())
                else:
                    words.append(word.capitalize())

            if words:
                parts.append(" ".join(words))

        return ", ".join(parts)
