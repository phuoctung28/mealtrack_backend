"""Domain port for canonical food-reference lookups."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class FoodReferenceServingProjection:
    """Food-specific serving conversion data."""

    name: str
    grams: float | None
    milliliters: float | None
    is_default: bool = False


@dataclass(frozen=True)
class FoodReferenceNutritionProjection:
    """Canonical nutrition snapshot used by catalog publication."""

    id: int
    name: str
    source: str
    is_verified: bool
    protein_100g: float | None
    carbs_100g: float | None
    fat_100g: float | None
    fiber_100g: float = 0.0
    sugar_100g: float = 0.0
    density_g_ml: float | None = None
    servings: list[FoodReferenceServingProjection] = field(default_factory=list)
    name_normalized: str | None = None


@dataclass(frozen=True)
class FoodReferenceSearchProjection:
    """Local food search result shaped before API response mapping."""

    id: int
    name: str
    name_normalized: str | None
    brand: str | None
    source: str
    is_verified: bool
    protein_100g: float | None
    carbs_100g: float | None
    fat_100g: float | None
    fiber_100g: float = 0.0
    sugar_100g: float = 0.0
    serving_size: str | None = None
    allowed_units: list[dict] = field(default_factory=list)


class FoodReferenceRepositoryPort(Protocol):
    """Repository contract for typed canonical food-reference projections."""

    async def get_nutrition_projection(
        self,
        food_reference_id: int,
    ) -> FoodReferenceNutritionProjection | None:
        """Return one canonical food-reference nutrition projection."""

    async def list_catalog_seed_candidates(
        self,
    ) -> list[FoodReferenceNutritionProjection]:
        """Return lightweight projections for catalog ingredient resolver ranking."""

    async def find_catalog_seed_candidates_by_normalized_name(
        self,
        name_normalized: str,
    ) -> list[FoodReferenceNutritionProjection]:
        """Return candidate projections by exact normalized name for seed imports."""

    async def search_local(
        self,
        query: str,
        region: str,
        limit: int,
    ) -> list[FoodReferenceSearchProjection]:
        """Return bounded, verified-first local search results."""
