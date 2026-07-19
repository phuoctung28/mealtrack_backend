"""Deterministic three-day meal recommendation optimizer."""

from __future__ import annotations

from src.domain.model.meal_recommendation import (
    CatalogMeal,
    MealRecommendationAlternative,
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
    RecipeScore,
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
        catalog_meals: list[CatalogMeal],
        *,
        daily_calories: int,
        affinity: IngredientAffinityProfile,
        cuisines: set[str] | None = None,
    ) -> MealRecommendationPlan | MealRecommendationInsufficiency:
        candidates = _filter_supported_catalog_meals(catalog_meals, cuisines)
        if len({catalog_meal.id for catalog_meal in candidates}) < PLAN_DAYS * len(MEAL_TYPE_ORDER):
            return MealRecommendationInsufficiency(
                reason=MealRecommendationInsufficiencyReason.NOT_ENOUGH_CURRENT_RECIPES,
                message="not enough unique catalog_meals for 3-day plan",
                required=PLAN_DAYS * len(MEAL_TYPE_ORDER),
                available=len({catalog_meal.id for catalog_meal in candidates}),
            )

        allocations = self._allocation.allocate(daily_calories)
        ranked_pools = {
            meal_type: self._scoring.rank(
                candidates,
                meal_type=meal_type,
                target_calories=allocations[meal_type],
                affinity=affinity,
            )
            for meal_type in MEAL_TYPE_ORDER
        }
        selected_ids: set[str] = set()
        slots: list[MealRecommendationSlot] = []

        for day_index in range(PLAN_DAYS):
            for meal_type in MEAL_TYPE_ORDER:
                target_calories = allocations[meal_type]
                ranked = self._rank_pool_with_fallback(
                    ranked_pools[meal_type],
                    target_calories=target_calories,
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
                selected_ids.add(winner.catalog_meal.id)
                slots.append(
                    MealRecommendationSlot(
                        day_index=day_index,
                        meal_type=meal_type,
                        target_calories=target_calories,
                        catalog_meal=winner.catalog_meal,
                        score=winner.score,
                    )
                )

        alternatives = {}
        for slot in slots:
            result = self._select_alternatives_from_pool(
                ranked_pools[slot.meal_type],
                day_index=slot.day_index,
                meal_type=slot.meal_type,
                target_calories=slot.target_calories,
                selected_catalog_meal_id=slot.catalog_meal.id,
                selected_catalog_meal_ids=selected_ids,
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
        catalog_meals: list[CatalogMeal],
        *,
        meal_type: str,
        target_calories: int,
        affinity: IngredientAffinityProfile,
        selected_ids: set[str],
    ):
        ranked = self._scoring.rank(
            catalog_meals,
            meal_type=meal_type,
            target_calories=target_calories,
            affinity=affinity,
            excluded_catalog_meal_ids=selected_ids,
        )
        for tolerance in (0.20, 0.30):
            within_tolerance = [
                item
                for item in ranked
                if abs(item.catalog_meal.calories - target_calories) / target_calories
                <= tolerance
            ]
            if within_tolerance:
                return within_tolerance
        return sorted(
            ranked,
            key=lambda item: (
                abs(item.catalog_meal.calories - target_calories),
                -item.score,
                item.catalog_meal.id,
            ),
        )

    def _rank_pool_with_fallback(
        self,
        ranked_pool: list[RecipeScore],
        *,
        target_calories: int,
        selected_ids: set[str],
    ) -> list[RecipeScore]:
        ranked = [
            item
            for item in ranked_pool
            if item.catalog_meal.id not in selected_ids and item.catalog_meal.calories > 0
        ]
        for tolerance in (0.20, 0.30):
            within_tolerance = [
                item
                for item in ranked
                if abs(item.catalog_meal.calories - target_calories) / target_calories
                <= tolerance
            ]
            if within_tolerance:
                return within_tolerance
        return sorted(
            ranked,
            key=lambda item: (
                abs(item.catalog_meal.calories - target_calories),
                -item.score,
                item.catalog_meal.id,
            ),
        )

    def _select_alternatives_from_pool(
        self,
        ranked_pool: list[RecipeScore],
        *,
        day_index: int,
        meal_type: str,
        target_calories: int,
        selected_catalog_meal_id: str,
        selected_catalog_meal_ids: set[str],
        count: int = 5,
    ) -> tuple[MealRecommendationAlternative, ...] | MealRecommendationInsufficiency:
        excluded = set(selected_catalog_meal_ids)
        excluded.add(selected_catalog_meal_id)
        ranked = [
            item for item in ranked_pool if item.catalog_meal.id not in excluded
        ]
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
                catalog_meal=item.catalog_meal,
                score=item.score,
            )
            for item in ranked[:count]
        )


def _filter_supported_catalog_meals(
    catalog_meals: list[CatalogMeal],
    cuisines: set[str] | None,
) -> list[CatalogMeal]:
    filtered = [
        catalog_meal
        for catalog_meal in catalog_meals
        if catalog_meal.status == "published"
        and (cuisines is None or catalog_meal.cuisine in cuisines)
        and set(catalog_meal.meal_types).intersection(MEAL_TYPE_ORDER)
    ]
    return sorted(filtered, key=lambda catalog_meal: catalog_meal.id)
