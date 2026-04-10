"""
Food image search service with in-memory LRU cache (NM-72).
Search chain: Pexels → Unsplash → None.
Cache: 7-day TTL, max 5000 entries with LRU eviction.
"""
import logging
import time
from collections import OrderedDict
from typing import Optional

from src.domain.model.meal_discovery.food_image import FoodImageResult

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days
CACHE_MAX_ENTRIES = 5_000


class FoodImageSearchService:
    """
    Orchestrates food image search with Pexels → Unsplash fallback chain.
    Uses an LRU in-memory cache keyed by normalized query.
    Thread-safe enough for single-process asyncio (GIL protected).
    """

    def __init__(self):
        from src.infra.adapters.pexels_image_adapter import PexelsImageAdapter
        from src.infra.adapters.unsplash_image_adapter import UnsplashImageAdapter

        self._adapters = [PexelsImageAdapter(), UnsplashImageAdapter()]
        # OrderedDict used as LRU: {normalized_query: (FoodImageResult | None, expires_ts)}
        self._cache: OrderedDict = OrderedDict()

    async def search_food_image(self, query: str) -> Optional[FoodImageResult]:
        """
        Return a food image for the given English query, or None if unavailable.
        Never raises — all errors are caught and logged.
        """
        key = self._normalize(query)

        # Cache hit
        cached = self._cache.get(key)
        if cached is not None:
            result, expires_ts = cached
            if time.time() < expires_ts:
                self._cache.move_to_end(key)  # LRU refresh
                return result
            else:
                del self._cache[key]

        # Search via adapter chain
        result = None
        for adapter in self._adapters:
            try:
                result = await adapter.search(query)
                if result is not None:
                    break
            except Exception as e:
                logger.warning(f"Image adapter {adapter.__class__.__name__} error: {e}")

        # Store in cache (including None to avoid repeated failed lookups)
        self._evict_if_needed()
        self._cache[key] = (result, time.time() + CACHE_TTL_SECONDS)
        self._cache.move_to_end(key)

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(query: str) -> str:
        return query.strip().lower()

    def _evict_if_needed(self) -> None:
        """Remove oldest entries when cache exceeds max size."""
        while len(self._cache) >= CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)  # Remove oldest (LRU front)


# Module-level singleton
_food_image_search_service: Optional[FoodImageSearchService] = None


def get_food_image_search_service() -> FoodImageSearchService:
    """Return the singleton FoodImageSearchService instance."""
    global _food_image_search_service
    if _food_image_search_service is None:
        _food_image_search_service = FoodImageSearchService()
    return _food_image_search_service
