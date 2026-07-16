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


class FoodReferenceRepositoryPort(Protocol):
    """Repository contract for typed canonical food-reference projections."""

    async def get_nutrition_projection(
        self,
        food_reference_id: int,
    ) -> FoodReferenceNutritionProjection | None:
        """Return one canonical food-reference nutrition projection."""
