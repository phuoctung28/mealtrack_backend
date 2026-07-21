"""Domain projections for curated catalog meals."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


@dataclass(frozen=True)
class CatalogMealIngredient:
    """Ingredient reference for a catalog meal."""

    food_reference_id: int
    display_name: str
    quantity: Decimal
    unit: str

    @property
    def name(self) -> str:
        """Compatibility for scoring/materialization call sites during rework."""

        return self.display_name


@dataclass(frozen=True)
class CatalogMeal:
    """Renderable catalog meal consumed by deterministic recommendation planning."""

    id: str
    catalog_key: str
    content_hash: str
    name: str
    cuisine: str
    description: str | None
    image_url: str | None
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal
    sugar_g: Decimal = Decimal("0")
    meal_types: tuple[str, ...] = field(default_factory=tuple)
    ingredients: tuple[CatalogMealIngredient, ...] = field(default_factory=tuple)
    is_active: bool = True

    @property
    def calories(self) -> int:
        """Backend-derived calories from macro totals."""

        protein = float(self.protein_g)
        carbs = float(self.carbs_g)
        fat = float(self.fat_g)
        fiber = float(self.fiber_g)
        return round(protein * 4 + max(0.0, carbs - fiber) * 4 + fiber * 2 + fat * 9)

    @property
    def status(self) -> str:
        """Compatibility for optimizer filtering during the rework."""

        return "published" if self.is_active else "retired"


class MealRecommendationInsufficiencyReason(StrEnum):
    """Typed reasons a deterministic recommendation plan cannot be produced."""

    NOT_ENOUGH_CURRENT_RECIPES = "not_enough_current_recipes"
    NOT_ENOUGH_ALTERNATIVES = "not_enough_alternatives"


@dataclass(frozen=True)
class MealRecommendationSlot:
    """One selected catalog meal slot in a deterministic recommendation plan."""

    day_index: int
    meal_type: str
    target_calories: int
    catalog_meal: CatalogMeal
    score: float

    @property
    def recipe(self) -> CatalogMeal:
        """Temporary optimizer compatibility for older call sites."""

        return self.catalog_meal


@dataclass(frozen=True)
class MealRecommendationAlternative:
    """Alternative catalog meal for a selected recommendation slot."""

    day_index: int
    meal_type: str
    target_calories: int
    catalog_meal: CatalogMeal
    score: float

    @property
    def recipe(self) -> CatalogMeal:
        """Temporary optimizer compatibility for older call sites."""

        return self.catalog_meal


@dataclass(frozen=True)
class MealRecommendationPlan:
    """Pure-domain deterministic recommendation result."""

    slots: tuple[MealRecommendationSlot, ...]
    alternatives: dict[tuple[int, str], tuple[MealRecommendationAlternative, ...]]


@dataclass(frozen=True)
class MealRecommendationInsufficiency:
    """Typed deterministic failure when catalog capacity is insufficient."""

    reason: MealRecommendationInsufficiencyReason
    message: str
    required: int
    available: int
