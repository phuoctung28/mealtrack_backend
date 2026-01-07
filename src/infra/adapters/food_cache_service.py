"""
Food cache service that uses Redis when available, with in-memory fallback.

Memory safeguards:
- LRU eviction when max cache size exceeded
- Automatic cleanup of expired entries
- Configurable max cache size
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional

from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.infra.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService

logger = logging.getLogger(__name__)

# Default max cache sizes for in-memory fallback
DEFAULT_MAX_SEARCH_CACHE = 100
DEFAULT_MAX_FOOD_CACHE = 500


class FoodCacheService(FoodCacheServicePort):
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service
        self._search_cache: Dict[str, Any] = {}
        self._food_cache: Dict[int, Any] = {}
        
        # Max cache sizes (only applies to in-memory fallback)
        self.max_search_cache = int(os.getenv("MAX_SEARCH_CACHE_SIZE", DEFAULT_MAX_SEARCH_CACHE))
        self.max_food_cache = int(os.getenv("MAX_FOOD_CACHE_SIZE", DEFAULT_MAX_FOOD_CACHE))
        
        logger.info(
            f"FoodCacheService initialized: redis={'enabled' if cache_service else 'disabled'}, "
            f"max_search_cache={self.max_search_cache}, max_food_cache={self.max_food_cache}"
        )

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

        # Evict expired entries first
        self._evict_expired_search()
        
        # Evict LRU if at max capacity
        if len(self._search_cache) >= self.max_search_cache:
            self._evict_lru_search()
        
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

        # Evict expired entries first
        self._evict_expired_food()
        
        # Evict LRU if at max capacity
        if len(self._food_cache) >= self.max_food_cache:
            self._evict_lru_food()
        
        self._food_cache[fdc_id] = {"ttl": time.time() + ttl, "data": food_data}
    
    def _evict_expired_search(self) -> int:
        """Evict expired search cache entries."""
        now = time.time()
        expired_keys = [k for k, v in self._search_cache.items() if v["ttl"] < now]
        for key in expired_keys:
            del self._search_cache[key]
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired search cache entries")
        return len(expired_keys)
    
    def _evict_lru_search(self) -> Optional[str]:
        """Evict least recently used search cache entry."""
        if not self._search_cache:
            return None
        # Find entry with oldest TTL (proxy for LRU since we don't track access)
        lru_key = min(self._search_cache.keys(), key=lambda k: self._search_cache[k]["ttl"])
        del self._search_cache[lru_key]
        logger.debug(f"Evicted LRU search cache entry: {lru_key}")
        return lru_key
    
    def _evict_expired_food(self) -> int:
        """Evict expired food cache entries."""
        now = time.time()
        expired_keys = [k for k, v in self._food_cache.items() if v["ttl"] < now]
        for key in expired_keys:
            del self._food_cache[key]
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired food cache entries")
        return len(expired_keys)
    
    def _evict_lru_food(self) -> Optional[int]:
        """Evict least recently used food cache entry."""
        if not self._food_cache:
            return None
        # Find entry with oldest TTL (proxy for LRU since we don't track access)
        lru_key = min(self._food_cache.keys(), key=lambda k: self._food_cache[k]["ttl"])
        del self._food_cache[lru_key]
        logger.debug(f"Evicted LRU food cache entry: {lru_key}")
        return lru_key
