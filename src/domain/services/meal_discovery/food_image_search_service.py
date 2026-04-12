"""
Food image search service with in-memory LRU cache.
Search chain: adapter list (injected) → first hit wins.
Cache: 7-day TTL, max 5000 entries with LRU eviction.
"""
import logging
import time
from collections import OrderedDict
from typing import List, Optional

from src.domain.model.meal_discovery.food_image import FoodImageResult
from src.domain.ports.food_image_search_port import FoodImageSearchPort

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days
CACHE_MAX_ENTRIES = 5_000


class FoodImageSearchService:
    """
    Orchestrates food image search with adapter fallback chain.
    Uses an LRU in-memory cache keyed by normalized query.
    """

    def __init__(self, adapters: List[FoodImageSearchPort]):
        self._adapters = adapters
        self._cache: OrderedDict = OrderedDict()

    async def search_food_image(self, query: str) -> Optional[FoodImageResult]:
        """Return a food image for the given query, or None. Never raises."""
        key = self._normalize(query)

        cached = self._cache.get(key)
        if cached is not None:
            result, expires_ts = cached
            if time.time() < expires_ts:
                self._cache.move_to_end(key)
                return result
            else:
                del self._cache[key]

        result = None
        for adapter in self._adapters:
            try:
                result = await adapter.search(query)
                if result is not None:
                    break
            except Exception as e:
                logger.warning(f"Image adapter {adapter.__class__.__name__} error: {e}")

        self._evict_if_needed()
        self._cache[key] = (result, time.time() + CACHE_TTL_SECONDS)
        self._cache.move_to_end(key)

        return result

    @staticmethod
    def _normalize(query: str) -> str:
        return query.strip().lower()

    def _evict_if_needed(self) -> None:
        while len(self._cache) >= CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)
