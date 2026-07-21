"""Process-local immutable catalog meal snapshot."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationCatalogUnavailableError,
)
from src.domain.model.meal_recommendation import CatalogMeal
from src.domain.ports.catalog_recipe_repository_port import CatalogMealRevision
from src.domain.services.meal_recommendation.catalog_ingredient_statistics_service import (
    CatalogIngredientStatistics,
    CatalogIngredientStatisticsService,
)
from src.observability import increment_metric


@dataclass(frozen=True)
class CatalogMealSnapshot:
    """Immutable active catalog snapshot for deterministic recommendation generation."""

    revision: CatalogMealRevision
    meals: tuple[CatalogMeal, ...]
    ingredient_statistics: CatalogIngredientStatistics
    refreshed_at: float
    expires_at: float


class CatalogMealSnapshotService:
    """Cache active catalog meals once per process and catalog revision."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 300,
        failure_retry_seconds: float = 30,
        clock: Callable[[], float] = monotonic,
        statistics_service: CatalogIngredientStatisticsService | None = None,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._failure_retry_seconds = failure_retry_seconds
        self._clock = clock
        self._statistics_service = statistics_service or CatalogIngredientStatisticsService()
        self._lock = asyncio.Lock()
        self._snapshot: CatalogMealSnapshot | None = None
        self._next_refresh_after = 0.0

    async def get_snapshot(self, uow) -> CatalogMealSnapshot:
        now = self._clock()
        snapshot = self._snapshot
        if snapshot is not None and snapshot.expires_at > now:
            return snapshot

        revision = await uow.catalog_recipes.get_active_catalog_revision()
        snapshot = self._snapshot
        if (
            snapshot is not None
            and snapshot.revision == revision
            and snapshot.expires_at > now
        ):
            return snapshot
        if snapshot is not None and snapshot.revision == revision:
            refreshed = CatalogMealSnapshot(
                revision=snapshot.revision,
                meals=snapshot.meals,
                ingredient_statistics=snapshot.ingredient_statistics,
                refreshed_at=snapshot.refreshed_at,
                expires_at=now + self._ttl_seconds,
            )
            self._snapshot = refreshed
            return refreshed

        return await self._refresh_singleflight(uow, expected_revision=revision)

    async def _refresh_singleflight(
        self,
        uow,
        *,
        expected_revision: CatalogMealRevision,
    ) -> CatalogMealSnapshot:
        async with self._lock:
            now = self._clock()
            current = self._snapshot
            if (
                current is not None
                and current.revision == expected_revision
                and current.expires_at > now
            ):
                return current
            if current is not None and now < self._next_refresh_after:
                return current

            try:
                meals = tuple(await uow.catalog_recipes.list_active_meals())
                loaded_revision = await uow.catalog_recipes.get_active_catalog_revision()
                if loaded_revision != expected_revision:
                    meals = tuple(await uow.catalog_recipes.list_active_meals())
                    loaded_revision = await uow.catalog_recipes.get_active_catalog_revision()
                if not meals:
                    raise MealRecommendationCatalogUnavailableError
                snapshot = CatalogMealSnapshot(
                    revision=loaded_revision,
                    meals=meals,
                    ingredient_statistics=self._statistics_service.build(meals),
                    refreshed_at=now,
                    expires_at=now + self._ttl_seconds,
                )
                self._snapshot = snapshot
                self._next_refresh_after = 0.0
                increment_metric(
                    "meal_recommendation.catalog_snapshot.refresh",
                    attributes={"status": "success"},
                )
                return snapshot
            except Exception:
                if current is not None:
                    self._next_refresh_after = now + self._failure_retry_seconds
                    increment_metric(
                        "meal_recommendation.catalog_snapshot.refresh",
                        attributes={"status": "last_good"},
                    )
                    return current
                increment_metric(
                    "meal_recommendation.catalog_snapshot.refresh",
                    attributes={"status": "cold_failure"},
                )
                raise
