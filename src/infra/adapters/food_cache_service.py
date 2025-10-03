"""
Simple in-memory cache service interface and a fallback no-op for USDA responses.
Replace with Redis later.
"""
from typing import Dict, Any, List, Optional
import time


from src.domain.ports.food_cache_service_port import FoodCacheServicePort


class FoodCacheService(FoodCacheServicePort):
    def __init__(self):
        self._search_cache: Dict[str, Any] = {}
        self._food_cache: Dict[int, Any] = {}

    async def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        entry = self._search_cache.get(query)
        if not entry:
            return None
        if entry["ttl"] < time.time():
            self._search_cache.pop(query, None)
            return None
        return entry["data"]

    async def cache_search(self, query: str, results: List[Dict[str, Any]], ttl: int = 3600):
        self._search_cache[query] = {"ttl": time.time() + ttl, "data": results}

    async def get_cached_food(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        entry = self._food_cache.get(fdc_id)
        if not entry:
            return None
        if entry["ttl"] < time.time():
            self._food_cache.pop(fdc_id, None)
            return None
        return entry["data"]

    async def cache_food(self, fdc_id: int, food_data: Dict[str, Any], ttl: int = 86400):
        self._food_cache[fdc_id] = {"ttl": time.time() + ttl, "data": food_data}
