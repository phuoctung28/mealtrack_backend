"""Abstract cache port — domain defines the contract, infra implements it."""
from abc import ABC, abstractmethod
from typing import Any, Optional


class CachePort(ABC):
    """Interface for cache operations used by application handlers."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Return cached value or None if missing/expired."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store value under key with TTL."""

    @abstractmethod
    async def invalidate(self, key: str) -> bool:
        """Delete a single cache entry. Returns True if the key existed."""

    @abstractmethod
    async def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern. Returns count of deleted keys."""
