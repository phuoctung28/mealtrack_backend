"""Synchronous Redis connection for RQ.

Note: RQ requires the sync `redis.Redis` client (not redis.asyncio).
"""

from __future__ import annotations

from functools import lru_cache

from redis import Redis

from src.infra.config.settings import settings


@lru_cache
def get_rq_redis_connection() -> Redis:
    """Return a singleton sync Redis connection for RQ."""
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
    )

