"""
Food cache service that uses Redis for caching.

If Redis is not available, cache operations are silently ignored to prevent
memory leaks from in-memory storage.
"""
import logging
from typing import Any, Dict, List, Optional

from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.food_cache_service_port import FoodCacheServicePort
from src.infra.cache.cache_service import CacheService

logger = logging.getLogger(__name__)


class FoodCacheService(FoodCacheServicePort):
    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service
        
        if cache_service:
            logger.info("FoodCacheService initialized with Redis cache")
        else:
            logger.warning(
                "FoodCacheService initialized without Redis. "
                "Cache operations will be ignored to prevent memory leaks."
            )

    async def get_cached_search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached search results from Redis if available."""
        if not self.cache_service:
            return None
        
        cache_key, _ = CacheKeys.food_search(query)
        return await self.cache_service.get_json(cache_key)

    async def cache_search(self, query: str, results: List[Dict[str, Any]], ttl: int = 3600):
        """Cache search results in Redis if available. Silently ignored if Redis unavailable."""
        if not self.cache_service:
            return
        
        cache_key, default_ttl = CacheKeys.food_search(query)
        await self.cache_service.set_json(cache_key, results, ttl or default_ttl)

    async def get_cached_food(self, fdc_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve cached food details from Redis if available."""
        if not self.cache_service:
            return None
        
        cache_key, _ = CacheKeys.food_details(str(fdc_id))
        return await self.cache_service.get_json(cache_key)

    async def cache_food(self, fdc_id: int, food_data: Dict[str, Any], ttl: int = 86400):
        """Cache food details in Redis if available. Silently ignored if Redis unavailable."""
        if not self.cache_service:
            return
        
        cache_key, default_ttl = CacheKeys.food_details(str(fdc_id))
        await self.cache_service.set_json(cache_key, food_data, ttl or default_ttl)
