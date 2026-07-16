"""Deterministic recipe scoring for meal recommendation candidates."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.model.meal_recommendation import CatalogRecipeVersion
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
)


@dataclass(frozen=True)
class RecipeScore:
    """Score plus deterministic tie-break identity."""

    recipe: CatalogRecipeVersion
    score: float


class RecipeScoringService:
    """Score immutable recipe versions without learned popularity or randomness."""

    def score(
        self,
        recipe: CatalogRecipeVersion,
        *,
        target_calories: int,
        affinity: IngredientAffinityProfile,
    ) -> RecipeScore:
        if target_calories <= 0:
            raise ValueError("target_calories must be positive")

        calorie_distance = abs(recipe.calories - target_calories) / target_calories
        calorie_fit = max(0.0, 1.0 - min(calorie_distance, 1.0))
        affinity_fit = _ingredient_affinity(recipe, affinity)
        score = round((calorie_fit * 0.82) + (affinity_fit * 0.18), 6)
        return RecipeScore(recipe=recipe, score=score)

    def rank(
        self,
        recipes: list[CatalogRecipeVersion],
        *,
        meal_type: str,
        target_calories: int,
        affinity: IngredientAffinityProfile,
        excluded_recipe_ids: set[str] | None = None,
    ) -> list[RecipeScore]:
        excluded_recipe_ids = excluded_recipe_ids or set()
        scored = [
            self.score(recipe, target_calories=target_calories, affinity=affinity)
            for recipe in recipes
            if recipe.id not in excluded_recipe_ids
            and meal_type in recipe.meal_types
            and recipe.calories > 0
        ]
        return sorted(scored, key=lambda item: (-item.score, item.recipe.id))


def _ingredient_affinity(
    recipe: CatalogRecipeVersion,
    affinity: IngredientAffinityProfile,
) -> float:
    if not affinity.weights or affinity.confidence <= 0:
        return 0.0
    ingredient_ids = {ingredient.food_reference_id for ingredient in recipe.ingredients}
    raw = sum(affinity.weights.get(food_id, 0.0) for food_id in ingredient_ids)
    return min(1.0, raw * affinity.confidence)

