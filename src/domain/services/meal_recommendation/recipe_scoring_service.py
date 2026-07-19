"""Deterministic catalog_meal scoring for meal recommendation candidates."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.model.meal_recommendation import CatalogMeal
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
)


@dataclass(frozen=True)
class RecipeScore:
    """Score plus deterministic tie-break identity."""

    catalog_meal: CatalogMeal
    score: float


class RecipeScoringService:
    """Score immutable catalog_meal versions without learned popularity or randomness."""

    def score(
        self,
        catalog_meal: CatalogMeal,
        *,
        target_calories: int,
        affinity: IngredientAffinityProfile,
    ) -> RecipeScore:
        if target_calories <= 0:
            raise ValueError("target_calories must be positive")

        calorie_distance = abs(catalog_meal.calories - target_calories) / target_calories
        calorie_fit = max(0.0, 1.0 - min(calorie_distance, 1.0))
        affinity_fit = _ingredient_affinity(catalog_meal, affinity)
        score = round((calorie_fit * 0.82) + (affinity_fit * 0.18), 6)
        return RecipeScore(catalog_meal=catalog_meal, score=score)

    def rank(
        self,
        catalog_meals: list[CatalogMeal],
        *,
        meal_type: str,
        target_calories: int,
        affinity: IngredientAffinityProfile,
        excluded_catalog_meal_ids: set[str] | None = None,
    ) -> list[RecipeScore]:
        excluded_catalog_meal_ids = excluded_catalog_meal_ids or set()
        scored = [
            self.score(catalog_meal, target_calories=target_calories, affinity=affinity)
            for catalog_meal in catalog_meals
            if catalog_meal.id not in excluded_catalog_meal_ids
            and meal_type in catalog_meal.meal_types
            and catalog_meal.calories > 0
        ]
        return sorted(scored, key=lambda item: (-item.score, item.catalog_meal.id))


def _ingredient_affinity(
    catalog_meal: CatalogMeal,
    affinity: IngredientAffinityProfile,
) -> float:
    if not affinity.weights or affinity.confidence <= 0:
        return 0.0
    ingredient_ids = {ingredient.food_reference_id for ingredient in catalog_meal.ingredients}
    raw = sum(affinity.weights.get(food_id, 0.0) for food_id in ingredient_ids)
    return min(1.0, raw * affinity.confidence)

