"""Domain projections for immutable catalog recipes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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

