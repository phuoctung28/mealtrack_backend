"""Resolve food identity and grams into deterministic nutrition."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.model.nutrition import MAX_FOOD_ITEM_QUANTITY, Macros


@dataclass(frozen=True)
class NutritionCandidate:
    """Per-100g structured nutrition data for a food candidate."""

    name: str
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: float = 0.0
    sugar_per_100g: float = 0.0
    source: str = "unknown"


@dataclass(frozen=True)
class ResolvedNutritionItem:
    """Resolved food item with scaled macros."""

    name: str
    grams: float
    macros: Macros
    source: str


class NutritionResolver:
    """Resolve recognized food names against structured nutrition data."""

    def __init__(self, local_candidates: dict[str, NutritionCandidate]) -> None:
        self._local_candidates = {
            key.strip().lower(): value for key, value in local_candidates.items()
        }

    async def resolve_item(
        self,
        *,
        name: str,
        estimated_grams: float,
    ) -> ResolvedNutritionItem:
        key = name.strip().lower()
        if not key:
            raise ValueError("food name must not be empty")
        if estimated_grams <= 0 or estimated_grams > MAX_FOOD_ITEM_QUANTITY:
            raise ValueError("estimated_grams must be within supported food quantity bounds")
        if key not in self._local_candidates:
            raise ValueError(f"No nutrition candidate found for food: {name}")

        candidate = self._local_candidates[key]
        factor = estimated_grams / 100.0
        return ResolvedNutritionItem(
            name=candidate.name,
            grams=estimated_grams,
            macros=Macros(
                protein=round(candidate.protein_per_100g * factor, 2),
                carbs=round(candidate.carbs_per_100g * factor, 2),
                fat=round(candidate.fat_per_100g * factor, 2),
                fiber=round(candidate.fiber_per_100g * factor, 2),
                sugar=round(candidate.sugar_per_100g * factor, 2),
            ),
            source=candidate.source,
        )
