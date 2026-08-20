"""Resolve and remember user meal scans so repeats return the same meal."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import Meal, MealStatus
from src.domain.ports.async_unit_of_work_port import AsyncUnitOfWorkPort
from src.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


def scan_source_for_mode(scan_mode: str) -> str:
    """Map scan_mode to the persisted Meal.source value."""
    return "food_label" if scan_mode == "food_label" else "scanner"


def content_fingerprint(image_bytes: bytes) -> str:
    """Stable fingerprint for raw upload bytes."""
    return hashlib.sha256(image_bytes).hexdigest()


class MealScanCacheService:
    """User-scoped meal scan cache backed by Redis + durable meal rows."""

    def __init__(
        self,
        uow: AsyncUnitOfWorkPort,
        cache: CachePort | None = None,
    ):
        self._uow = uow
        self._cache = cache

    async def get_by_image_id(
        self,
        *,
        user_id: str,
        image_id: str,
        source: str,
    ) -> Meal | None:
        """Return an existing READY meal for this user image scan, if any."""
        cached_meal_id = await self._get_cached_meal_id(
            user_id=user_id,
            cache_identity=image_id,
            source=source,
        )
        if cached_meal_id:
            meal = await self._load_ready_meal(cached_meal_id, user_id=user_id)
            if meal is not None:
                logger.info(
                    "[MEAL-SCAN-CACHE] hit redis user=%s image_id=%s meal=%s",
                    user_id,
                    image_id,
                    meal.meal_id,
                )
                return meal

        async with self._uow as uow:
            meal = await uow.meals.find_ready_by_user_and_image_id(
                user_id=user_id,
                image_id=image_id,
                source=source,
            )
        if meal is None:
            return None

        await self.remember(
            user_id=user_id,
            cache_identity=image_id,
            source=source,
            meal_id=meal.meal_id,
        )
        logger.info(
            "[MEAL-SCAN-CACHE] hit db user=%s image_id=%s meal=%s",
            user_id,
            image_id,
            meal.meal_id,
        )
        return meal

    async def get_by_content_fingerprint(
        self,
        *,
        user_id: str,
        fingerprint: str,
        source: str,
    ) -> Meal | None:
        """Return a READY meal previously cached for identical upload bytes."""
        cached_meal_id = await self._get_cached_meal_id(
            user_id=user_id,
            cache_identity=f"sha256:{fingerprint}",
            source=source,
        )
        if not cached_meal_id:
            return None
        meal = await self._load_ready_meal(cached_meal_id, user_id=user_id)
        if meal is not None:
            logger.info(
                "[MEAL-SCAN-CACHE] hit content user=%s meal=%s",
                user_id,
                meal.meal_id,
            )
        return meal

    async def remember(
        self,
        *,
        user_id: str,
        cache_identity: str,
        source: str,
        meal_id: str,
    ) -> None:
        """Store meal_id for a user scan identity."""
        if not self._cache:
            return
        key, ttl = CacheKeys.user_meal_scan(user_id, cache_identity, source)
        try:
            await self._cache.set(key, meal_id, ttl)
        except Exception as exc:
            logger.warning(
                "[MEAL-SCAN-CACHE] remember failed key=%s: %s",
                key,
                exc,
            )

    async def remember_image_scan(
        self,
        *,
        user_id: str,
        image_id: str,
        source: str,
        meal_id: str,
    ) -> None:
        await self.remember(
            user_id=user_id,
            cache_identity=image_id,
            source=source,
            meal_id=meal_id,
        )

    async def remember_content_scan(
        self,
        *,
        user_id: str,
        fingerprint: str,
        source: str,
        meal_id: str,
    ) -> None:
        await self.remember(
            user_id=user_id,
            cache_identity=f"sha256:{fingerprint}",
            source=source,
            meal_id=meal_id,
        )

    async def invalidate(
        self,
        *,
        user_id: str,
        image_id: str | None,
        source: str | None,
    ) -> None:
        """Drop Redis entry when a cached scanned meal is deleted."""
        if not self._cache or not image_id or not source:
            return
        key, _ = CacheKeys.user_meal_scan(user_id, image_id, source)
        try:
            await self._cache.invalidate(key)
        except Exception as exc:
            logger.warning(
                "[MEAL-SCAN-CACHE] invalidate failed key=%s: %s",
                key,
                exc,
            )

    async def _get_cached_meal_id(
        self,
        *,
        user_id: str,
        cache_identity: str,
        source: str,
    ) -> str | None:
        if not self._cache:
            return None
        key, _ = CacheKeys.user_meal_scan(user_id, cache_identity, source)
        try:
            value = await self._cache.get(key)
        except Exception as exc:
            logger.warning("[MEAL-SCAN-CACHE] get failed key=%s: %s", key, exc)
            return None
        if isinstance(value, str) and value:
            return value
        return None

    async def _load_ready_meal(self, meal_id: str, *, user_id: str) -> Meal | None:
        async with self._uow as uow:
            meal = await uow.meals.find_by_id(meal_id)
        if meal is None:
            return None
        if meal.user_id != user_id:
            return None
        if meal.status != MealStatus.READY:
            return None
        if meal.nutrition is None:
            return None
        return meal


def mark_scan_cache_hit(meal: Meal) -> Meal:
    """Annotate a meal so API callers can skip duplicate side effects."""
    meal._meal_scan_cache_hit = True  # type: ignore[attr-defined]
    meal._meal_value_insight_scheduled = True  # type: ignore[attr-defined]
    return meal


def is_scan_cache_hit(meal: Any) -> bool:
    return bool(getattr(meal, "_meal_scan_cache_hit", False))
