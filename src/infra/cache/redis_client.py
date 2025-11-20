"""
Async Redis client with connection pooling.
"""
from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisClient:
    """Wrapper around redis.asyncio client that manages a shared pool."""

    def __init__(self, redis_url: str, max_connections: int = 50):
        self._redis_url = redis_url
        self.pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            decode_responses=True,
        )
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Initialize the Redis connection."""
        if self.client is not None:
            return

        self.client = redis.Redis(connection_pool=self.pool)
        try:
            await self.client.ping()
            logger.info("Redis connected (%s)", self._redis_url)
        except RedisError as exc:  # pragma: no cover - connection errors logged
            logger.error("Failed to connect to Redis: %s", exc)
            raise

    async def disconnect(self) -> None:
        """Close Redis connections."""
        if self.client:
            await self.client.aclose()
            self.client = None

        await self.pool.disconnect()
        logger.info("Redis disconnected")

    async def get(self, key: str) -> Optional[str]:
        """Retrieve a cached value."""
        if not self.client:
            return None
        try:
            return await self.client.get(key)
        except RedisError as exc:
            logger.warning("Redis GET error for key %s: %s", key, exc)
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Store a value with optional TTL."""
        if not self.client:
            return False
        try:
            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
            return True
        except RedisError as exc:
            logger.warning("Redis SET error for key %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cached key."""
        if not self.client:
            return False
        try:
            await self.client.delete(key)
            return True
        except RedisError as exc:
            logger.warning("Redis DELETE error for key %s: %s", key, exc)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys that match a pattern."""
        if not self.client:
            return 0
        try:
            keys = await self.client.keys(pattern)
            if not keys:
                return 0
            return await self.client.delete(*keys)
        except RedisError as exc:
            logger.warning("Redis DELETE pattern error for %s: %s", pattern, exc)
            return 0

    async def exists(self, key: str) -> bool:
        """Return True if a key exists."""
        if not self.client:
            return False
        try:
            return bool(await self.client.exists(key))
        except RedisError as exc:
            logger.warning("Redis EXISTS error for key %s: %s", key, exc)
            return False

