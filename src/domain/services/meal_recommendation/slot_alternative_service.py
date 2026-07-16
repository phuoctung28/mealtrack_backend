"""Alternative selection for deterministic recommendation slots."""

from __future__ import annotations

from src.domain.model.meal_recommendation import (
    CatalogRecipeVersion,
    MealRecommendationAlternative,
    MealRecommendationInsufficiency,
    MealRecommendationInsufficiencyReason,
)
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
)
from src.domain.services.meal_recommendation.recipe_scoring_service import (
    RecipeScoringService,
)


class SlotAlternativeService:
    """Select five stable alternatives per slot from the same catalog snapshot."""

    def __init__(self, scoring: RecipeScoringService | None = None):
        self._scoring = scoring or RecipeScoringService()

    def select_alternatives(
        self,
        recipes: list[CatalogRecipeVersion],
        *,
        day_index: int,
        meal_type: str,
        target_calories: int,
        selected_recipe_id: str,
        selected_recipe_ids: set[str],
        affinity: IngredientAffinityProfile,
        count: int = 5,
    ) -> tuple[MealRecommendationAlternative, ...] | MealRecommendationInsufficiency:
        excluded = set(selected_recipe_ids)
        excluded.add(selected_recipe_id)
        ranked = self._scoring.rank(
            recipes,
            meal_type=meal_type,
            target_calories=target_calories,
            affinity=affinity,
            excluded_recipe_ids=excluded,
        )
        if len(ranked) < count:
            return MealRecommendationInsufficiency(
                reason=MealRecommendationInsufficiencyReason.NOT_ENOUGH_ALTERNATIVES,
                message=f"not enough alternatives for {meal_type}",
                required=count,
                available=len(ranked),
            )
        return tuple(
            MealRecommendationAlternative(
                day_index=day_index,
                meal_type=meal_type,
                target_calories=target_calories,
                recipe=item.recipe,
                score=item.score,
            )
            for item in ranked[:count]
        )

