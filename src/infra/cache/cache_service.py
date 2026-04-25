"""
High-level cache service that handles serialization and metrics.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, TypeVar

from pydantic import BaseModel

from src.domain.ports.cache_port import CachePort
from src.infra.cache.metrics import CacheMonitor
from src.infra.cache.redis_client import RedisClient

# Strip the trailing 'Z' produced by an older serializer bug that wrote
# tz-aware datetimes as '...+HH:MMZ' (offset + Z together is invalid ISO8601
# and rejected by Pydantic v2). Heals existing Redis entries on read.
_LEGACY_OFFSET_Z_RE = re.compile(r"([+-]\d{2}:\d{2})Z")

T = TypeVar("T")


class CacheService(CachePort):
    """Cache service implementing the cache-aside pattern."""

    def __init__(
        self,
        redis_client: RedisClient,
        default_ttl: int = 3600,
        monitor: Optional[CacheMonitor] = None,
        enabled: bool = True,
    ):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.monitor = monitor
        self.enabled = enabled

    async def get(self, key: str) -> Optional[Any]:
        """Implement CachePort.get — delegates to get_json."""
        return await self.get_json(key)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Implement CachePort.set — delegates to set_json."""
        await self.set_json(key, value, ttl_seconds)

    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and deserialize a cached JSON payload."""
        if not self.enabled:
            return None

        raw = await self.redis.get(key)
        if raw is None:
            if self.monitor:
                self.monitor.record_miss()
            return None

        if self.monitor:
            self.monitor.record_hit()

        try:
            sanitized = (
                _LEGACY_OFFSET_Z_RE.sub(r"\1", raw) if isinstance(raw, str) else raw
            )
            return json.loads(sanitized)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Serialize and cache a value."""
        if not self.enabled:
            return False

        payload: str
        if isinstance(value, BaseModel):
            payload = value.model_dump_json()
        else:
            payload = json.dumps(value, default=_json_serializer)

        return await self.redis.set(key, payload, ttl or self.default_ttl)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: Optional[int] = None,
    ) -> Optional[T]:
        """
        Cache-aside helper that fetches data from cache or executes the factory.
        """
        cached = await self.get_json(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        value = await factory()
        if value is not None:
            await self.set_json(key, value, ttl)
        return value

    async def invalidate(self, key: str) -> bool:
        """Remove a cached value."""
        if not self.enabled:
            return False
        return await self.redis.delete(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """Remove all cache keys matching a pattern."""
        if not self.enabled:
            return 0
        return await self.redis.delete_pattern(pattern)


def _json_serializer(value: Any) -> Any:
    """Helper to serialize objects that aren't JSON-serializable by default."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, datetime):
        # tz-aware datetimes already encode the offset (e.g. +00:00); only
        # append 'Z' for naive datetimes (assumed UTC) to avoid producing
        # malformed strings like '...+00:00Z' that Pydantic rejects.
        return (
            value.isoformat() if value.tzinfo is not None else value.isoformat() + "Z"
        )
    raise TypeError(
        f"Object of type {value.__class__.__name__} is not JSON serializable"
    )
