"""Deterministic three-day meal recommendation optimizer."""

from __future__ import annotations

from src.domain.model.meal_recommendation import (
    CatalogRecipeVersion,
    MealRecommendationInsufficiency,
    MealRecommendationInsufficiencyReason,
    MealRecommendationPlan,
    MealRecommendationSlot,
)
from src.domain.services.meal_recommendation.calorie_allocation_policy import (
    MEAL_TYPE_ORDER,
    CalorieAllocationPolicy,
)
from src.domain.services.meal_recommendation.ingredient_affinity_service import (
    IngredientAffinityProfile,
)
from src.domain.services.meal_recommendation.recipe_scoring_service import (
    RecipeScoringService,
)
from src.domain.services.meal_recommendation.slot_alternative_service import (
    SlotAlternativeService,
)

ALGORITHM_VERSION = "catalog_deterministic_v1"
PLAN_DAYS = 3


class ThreeDayPlanOptimizer:
    """Build deterministic 3-day plans from immutable catalog projections."""

    def __init__(
        self,
        allocation: CalorieAllocationPolicy | None = None,
        scoring: RecipeScoringService | None = None,
        alternatives: SlotAlternativeService | None = None,
    ):
        self._allocation = allocation or CalorieAllocationPolicy()
        self._scoring = scoring or RecipeScoringService()
        self._alternatives = alternatives or SlotAlternativeService(self._scoring)

    def build_plan(
        self,
        recipes: list[CatalogRecipeVersion],
        *,
        daily_calories: int,
        affinity: IngredientAffinityProfile,
        cuisines: set[str] | None = None,
    ) -> MealRecommendationPlan | MealRecommendationInsufficiency:
        candidates = _filter_supported_recipes(recipes, cuisines)
        if len({recipe.id for recipe in candidates}) < PLAN_DAYS * len(MEAL_TYPE_ORDER):
            return MealRecommendationInsufficiency(
                reason=MealRecommendationInsufficiencyReason.NOT_ENOUGH_CURRENT_RECIPES,
                message="not enough unique recipes for 3-day plan",
                required=PLAN_DAYS * len(MEAL_TYPE_ORDER),
                available=len({recipe.id for recipe in candidates}),
            )

        allocations = self._allocation.allocate(daily_calories)
        selected_ids: set[str] = set()
        slots: list[MealRecommendationSlot] = []

        for day_index in range(PLAN_DAYS):
            for meal_type in MEAL_TYPE_ORDER:
                target_calories = allocations[meal_type]
                ranked = self._rank_with_fallback(
                    candidates,
                    meal_type=meal_type,
                    target_calories=target_calories,
                    affinity=affinity,
                    selected_ids=selected_ids,
                )
                if not ranked:
                    return MealRecommendationInsufficiency(
                        reason=MealRecommendationInsufficiencyReason.NOT_ENOUGH_CURRENT_RECIPES,
                        message=f"not enough unique candidates for {meal_type}",
                        required=1,
                        available=0,
                    )
                winner = ranked[0]
                selected_ids.add(winner.recipe.id)
                slots.append(
                    MealRecommendationSlot(
                        day_index=day_index,
                        meal_type=meal_type,
                        target_calories=target_calories,
                        recipe=winner.recipe,
                        score=winner.score,
                    )
                )

        alternatives = {}
        for slot in slots:
            result = self._alternatives.select_alternatives(
                candidates,
                day_index=slot.day_index,
                meal_type=slot.meal_type,
                target_calories=slot.target_calories,
                selected_recipe_id=slot.recipe.id,
                selected_recipe_ids=selected_ids,
                affinity=affinity,
            )
            if isinstance(result, MealRecommendationInsufficiency):
                return result
            alternatives[(slot.day_index, slot.meal_type)] = result

        return MealRecommendationPlan(
            algorithm_version=ALGORITHM_VERSION,
            slots=tuple(slots),
            alternatives=alternatives,
        )

    def _rank_with_fallback(
        self,
        recipes: list[CatalogRecipeVersion],
        *,
        meal_type: str,
        target_calories: int,
        affinity: IngredientAffinityProfile,
        selected_ids: set[str],
    ):
        ranked = self._scoring.rank(
            recipes,
            meal_type=meal_type,
            target_calories=target_calories,
            affinity=affinity,
            excluded_recipe_ids=selected_ids,
        )
        for tolerance in (0.20, 0.30):
            within_tolerance = [
                item
                for item in ranked
                if abs(item.recipe.calories - target_calories) / target_calories
                <= tolerance
            ]
            if within_tolerance:
                return within_tolerance
        return sorted(
            ranked,
            key=lambda item: (
                abs(item.recipe.calories - target_calories),
                -item.score,
                item.recipe.id,
            ),
        )


def _filter_supported_recipes(
    recipes: list[CatalogRecipeVersion],
    cuisines: set[str] | None,
) -> list[CatalogRecipeVersion]:
    filtered = [
        recipe
        for recipe in recipes
        if recipe.status == "published"
        and (cuisines is None or recipe.cuisine in cuisines)
        and set(recipe.meal_types).intersection(MEAL_TYPE_ORDER)
    ]
    return sorted(filtered, key=lambda recipe: recipe.id)
