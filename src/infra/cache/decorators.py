"""
Cache decorators for wrapping async service calls.
"""
from __future__ import annotations

from functools import wraps
from typing import Awaitable, Callable, Optional

from src.infra.cache.cache_service import CacheService


def cached(
    key_func: Callable[..., str],
    ttl: Optional[int] = None,
):
    """
    Decorator to transparently cache async method results.

    The wrapped function must be an async method whose first argument is `self`
    and `self` must expose a `cache_service` attribute.
    """

    def decorator(func: Callable[..., Awaitable]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            self_obj = args[0]
            cache_service: CacheService = getattr(self_obj, "cache_service", None)

            if cache_service is None:
                return await func(*args, **kwargs)

            cache_key = key_func(*args, **kwargs)
            cached_value = await cache_service.get_json(cache_key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            if result is not None:
                await cache_service.set_json(cache_key, result, ttl)
            return result

        return wrapper

    return decorator

