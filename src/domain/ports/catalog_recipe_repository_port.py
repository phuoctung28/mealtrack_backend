"""Repository port for curated catalog meal projections."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.model.meal_recommendation.catalog_recipe import CatalogMeal


class CatalogMealRepositoryPort(ABC):
    """Read/write contract for catalog meals during the rework."""

    @abstractmethod
    async def list_active_meals(
        self,
        *,
        cuisine: str | None = None,
        meal_type: str | None = None,
    ) -> list[CatalogMeal]:
        """Return active catalog meals."""

    @abstractmethod
    async def get_meal(self, catalog_meal_id: str) -> CatalogMeal | None:
        """Return one active catalog meal."""
