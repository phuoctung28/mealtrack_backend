"""Domain projections for immutable catalog recipes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True)
class CatalogRecipeIngredient:
    """Ingredient snapshot for a published catalog recipe version."""

    food_reference_id: int
    name: str
    quantity: float
    unit: str
    resolved_grams: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    position: int = 0
    is_display_only: bool = False


@dataclass(frozen=True)
class CatalogRecipeVersion:
    """Immutable recipe version consumed by recommendation planning."""

    id: str
    recipe_id: str
    release_id: str
    recipe_key: str
    name: str
    cuisine: str
    status: str
    version_number: int
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    meal_types: tuple[str, ...] = field(default_factory=tuple)
    ingredients: tuple[CatalogRecipeIngredient, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CatalogRelease:
    """Recipe catalog release metadata."""

    id: str
    release_key: str
    manifest_digest: str
    status: str
    expected_recipe_count: int
    activated_at: datetime | None = None


class MealRecommendationInsufficiencyReason(StrEnum):
    """Typed reasons a deterministic recommendation plan cannot be produced."""

    NOT_ENOUGH_CURRENT_RECIPES = "not_enough_current_recipes"
    NOT_ENOUGH_ALTERNATIVES = "not_enough_alternatives"


@dataclass(frozen=True)
class MealRecommendationSlot:
    """One selected recipe slot in a deterministic recommendation plan."""

    day_index: int
    meal_type: str
    target_calories: int
    recipe: CatalogRecipeVersion
    score: float


@dataclass(frozen=True)
class MealRecommendationAlternative:
    """Alternative recipe for a selected recommendation slot."""

    day_index: int
    meal_type: str
    target_calories: int
    recipe: CatalogRecipeVersion
    score: float


@dataclass(frozen=True)
class MealRecommendationPlan:
    """Pure-domain deterministic recommendation result."""

    algorithm_version: str
    slots: tuple[MealRecommendationSlot, ...]
    alternatives: dict[tuple[int, str], tuple[MealRecommendationAlternative, ...]]


@dataclass(frozen=True)
class MealRecommendationInsufficiency:
    """Typed deterministic failure when catalog capacity is insufficient."""

    reason: MealRecommendationInsufficiencyReason
    message: str
    required: int
    available: int
