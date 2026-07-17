"""Repository port for curated catalog meal projections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.model.meal_recommendation.catalog_recipe import CatalogMeal


@dataclass(frozen=True)
class CatalogMealSeedIngredientWrite:
    """Ingredient payload for additive catalog seed imports."""

    food_reference_id: int
    display_name: str
    quantity: float
    unit: str


@dataclass(frozen=True)
class CatalogMealSeedWrite:
    """Display-only meal payload for additive catalog seed imports."""

    catalog_key: str
    content_hash: str
    name: str
    cuisine: str
    description: str | None
    image_url: str | None
    meal_types: tuple[str, ...]
    ingredients: tuple[CatalogMealSeedIngredientWrite, ...]


@dataclass(frozen=True)
class CatalogMealSeedExisting:
    """Minimal existing-row projection used for duplicate protection."""

    catalog_key: str
    content_hash: str


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

    @abstractmethod
    async def find_seed_existing(
        self,
        *,
        catalog_key: str,
        content_hash: str,
    ) -> CatalogMealSeedExisting | None:
        """Return an existing catalog seed row by key or content hash."""

    @abstractmethod
    async def add_seed_meal(self, seed: CatalogMealSeedWrite) -> None:
        """Add one display-only catalog seed meal without owning commit."""
