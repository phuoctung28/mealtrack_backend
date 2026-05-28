"""Helpers for caching Firebase UID to active user ID lookups."""

from __future__ import annotations

import logging
from typing import Optional

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# 10-minute in-process cache. Avoids a Redis round-trip on every authenticated
# request. maxsize=500 is sufficient at current traffic levels (56 req/min peak),
# saving ~15 MB per worker vs the previous 15k limit.
_uid_cache: TTLCache[str, dict] = TTLCache(maxsize=500, ttl=600)


async def get_cached_user_id(
    cache_service,  # kept for signature compatibility, no longer used
    firebase_uid: str,
) -> Optional[str]:
    """Return cached database user ID only when the cached user is active."""
    entry = _uid_cache.get(firebase_uid)
    if not isinstance(entry, dict) or entry.get("is_active") is not True:
        return None
    user_id = entry.get("user_id")
    return str(user_id) if user_id else None


async def set_cached_user_id(
    cache_service,  # kept for signature compatibility, no longer used
    firebase_uid: str,
    user_id: str,
    is_active: bool,
) -> None:
    """Cache database user identity for the Firebase UID."""
    _uid_cache[firebase_uid] = {"user_id": str(user_id), "is_active": bool(is_active)}


async def invalidate_cached_user_id(
    cache_service,  # kept for signature compatibility, no longer used
    firebase_uid: str,
) -> None:
    """Invalidate cached Firebase UID mapping."""
    _uid_cache.pop(firebase_uid, None)
