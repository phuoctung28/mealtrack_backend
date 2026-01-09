"""
Enhanced cache decorators for wrapping async service calls.
Provides consistent caching patterns across the application.
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
from typing import Awaitable, Callable, Optional, TypeVar, ParamSpec

from src.domain.cache.cache_keys import CacheKeys
from src.infra.cache.cache_service import CacheService

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def cached(
    key_func: Callable[..., str],
    ttl: Optional[int] = None,
    cache_none: bool = False,
):
    """
    Decorator to transparently cache async method results.
    
    Args:
        key_func: Function to generate cache key from args
        ttl: Time-to-live in seconds (None uses default)
        cache_none: Whether to cache None results (default False)
    
    The wrapped function must be an async method whose first argument is `self`
    and `self` must expose a `cache_service` attribute.
    
    Example:
        class MyService:
            def __init__(self, cache_service: CacheService):
                self.cache_service = cache_service
            
            @cached(key_func=lambda self, user_id: f"user:data:{user_id}", ttl=3600)
            async def get_user_data(self, user_id: str) -> dict:
                return await self._fetch_from_db(user_id)
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            self_obj = args[0]
            cache_service: CacheService = getattr(self_obj, "cache_service", None)

            if cache_service is None:
                return await func(*args, **kwargs)

            cache_key = key_func(*args, **kwargs)
            
            try:
                cached_value = await cache_service.get_json(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return cached_value
            except Exception as e:
                logger.warning(f"Cache GET failed: {cache_key} - {e}")

            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)
            
            if result is not None or cache_none:
                try:
                    await cache_service.set_json(cache_key, result, ttl)
                except Exception as e:
                    logger.warning(f"Cache SET failed: {cache_key} - {e}")
            
            return result

        return wrapper
    return decorator


def cached_method(
    prefix: str,
    ttl: int = CacheKeys.TTL_1_HOUR,
    include_args: bool = True,
):
    """
    Simplified decorator that auto-generates cache keys.
    
    Args:
        prefix: Cache key prefix (e.g., "user:profile")
        ttl: Time-to-live in seconds
        include_args: Whether to include args in cache key
    
    Example:
        @cached_method(prefix="food:search", ttl=CacheKeys.TTL_7_DAYS)
        async def search_foods(self, query: str) -> List[Food]:
            return await self._api.search(query)
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            self_obj = args[0]
            cache_service: CacheService = getattr(self_obj, "cache_service", None)

            if cache_service is None:
                return await func(*args, **kwargs)

            # Generate cache key
            if include_args:
                # Hash args and kwargs for key
                key_data = json.dumps(
                    {"args": args[1:], "kwargs": kwargs},
                    sort_keys=True,
                    default=str
                )
                key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
                cache_key = f"{prefix}:{key_hash}"
            else:
                cache_key = prefix

            try:
                cached_value = await cache_service.get_json(cache_key)
                if cached_value is not None:
                    return cached_value
            except Exception as e:
                logger.warning(f"Cache GET failed: {cache_key} - {e}")

            result = await func(*args, **kwargs)
            
            if result is not None:
                try:
                    await cache_service.set_json(cache_key, result, ttl)
                except Exception as e:
                    logger.warning(f"Cache SET failed: {cache_key} - {e}")
            
            return result

        return wrapper
    return decorator


def invalidate_on_write(
    key_patterns: list[str] | Callable[..., list[str]],
):
    """
    Decorator that invalidates cache keys after a write operation.
    
    Args:
        key_patterns: List of cache key patterns to invalidate,
                      or a function that returns patterns based on args
    
    Example:
        @invalidate_on_write(
            key_patterns=lambda self, user_id, **_: [f"user:profile:{user_id}"]
        )
        async def update_user(self, user_id: str, data: dict):
            await self._db.update(user_id, data)
    """
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Execute the write operation first
            result = await func(*args, **kwargs)
            
            # Get cache service
            self_obj = args[0]
            cache_service: CacheService = getattr(self_obj, "cache_service", None)
            
            if cache_service is None:
                return result
            
            # Get patterns to invalidate
            if callable(key_patterns):
                patterns = key_patterns(*args, **kwargs)
            else:
                patterns = key_patterns
            
            # Invalidate each pattern
            for pattern in patterns:
                try:
                    if "*" in pattern:
                        await cache_service.invalidate_pattern(pattern)
                    else:
                        await cache_service.invalidate(pattern)
                    logger.debug(f"Cache invalidated: {pattern}")
                except Exception as e:
                    logger.warning(f"Cache invalidation failed: {pattern} - {e}")
            
            return result

        return wrapper
    return decorator


# Convenience TTL constants for common use cases
class CacheTTL:
    """Common cache TTL values."""
    
    VERY_SHORT = 60          # 1 minute - for frequently changing data
    SHORT = 300              # 5 minutes - for session-like data
    MEDIUM = 3600            # 1 hour - for user preferences
    LONG = 86400             # 1 day - for TDEE, daily aggregates
    VERY_LONG = 604800       # 1 week - for food data, static content
    PERMANENT = 2592000      # 30 days - for rarely changing data
