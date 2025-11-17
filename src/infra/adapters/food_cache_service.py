"""
Food cache service that uses Redis when available, with in-memory fallback.
"""
import time
from typing import Any, Dict, List, Optional

from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.infra.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService


class FoodCacheService(FoodCacheServicePort):
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service
        self._search_cache: Dict[str, Any] = {}
        self._food_cache: Dict[int, Any] = {}

    async def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        if self.cache_service:
            cache_key, _ = CacheKeys.food_search(query)
            return await self.cache_service.get_json(cache_key)

        entry = self._search_cache.get(query)
        if not entry or entry["ttl"] < time.time():
            self._search_cache.pop(query, None)
            return None
        return entry["data"]

    async def cache_search(self, query: str, results: List[Dict[str, Any]], ttl: int = 3600):
        if self.cache_service:
            cache_key, default_ttl = CacheKeys.food_search(query)
            await self.cache_service.set_json(cache_key, results, ttl or default_ttl)
            return

        self._search_cache[query] = {"ttl": time.time() + ttl, "data": results}

    async def get_cached_food(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        if self.cache_service:
            cache_key, _ = CacheKeys.food_details(str(fdc_id))
            return await self.cache_service.get_json(cache_key)

        entry = self._food_cache.get(fdc_id)
        if not entry or entry["ttl"] < time.time():
            self._food_cache.pop(fdc_id, None)
            return None
        return entry["data"]

    async def cache_food(self, fdc_id: int, food_data: Dict[str, Any], ttl: int = 86400):
        if self.cache_service:
            cache_key, default_ttl = CacheKeys.food_details(str(fdc_id))
            await self.cache_service.set_json(cache_key, food_data, ttl or default_ttl)
            return

        self._food_cache[fdc_id] = {"ttl": time.time() + ttl, "data": food_data}
