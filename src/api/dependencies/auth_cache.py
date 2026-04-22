"""Helpers for caching Firebase UID to active user ID lookups."""

from __future__ import annotations

import logging
from typing import Optional

from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


async def get_cached_user_id(
    cache_service: Optional[CachePort],
    firebase_uid: str,
) -> Optional[str]:
    """Return cached database user ID only when the cached user is active."""
    if not cache_service:
        return None

    cache_key, _ = CacheKeys.auth_uid_to_user(firebase_uid)
    try:
        cached = await cache_service.get(cache_key)
    except Exception as exc:
        logger.warning("Auth cache read failed for uid=%s: %s", firebase_uid, exc)
        return None

    if not isinstance(cached, dict) or cached.get("is_active") is not True:
        return None

    user_id = cached.get("user_id")
    return str(user_id) if user_id else None


async def set_cached_user_id(
    cache_service: Optional[CachePort],
    firebase_uid: str,
    user_id: str,
    is_active: bool,
) -> None:
    """Cache database user identity for the Firebase UID."""
    if not cache_service:
        return

    cache_key, ttl = CacheKeys.auth_uid_to_user(firebase_uid)
    try:
        await cache_service.set(
            cache_key,
            {"user_id": str(user_id), "is_active": bool(is_active)},
            ttl,
        )
    except Exception as exc:
        logger.warning("Auth cache write failed for uid=%s: %s", firebase_uid, exc)


async def invalidate_cached_user_id(
    cache_service: Optional[CachePort],
    firebase_uid: str,
) -> None:
    """Invalidate cached Firebase UID mapping."""
    if not cache_service:
        return

    cache_key, _ = CacheKeys.auth_uid_to_user(firebase_uid)
    try:
        await cache_service.invalidate(cache_key)
    except Exception as exc:
        logger.warning(
            "Auth cache invalidation failed for uid=%s: %s", firebase_uid, exc
        )
