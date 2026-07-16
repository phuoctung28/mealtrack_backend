"""Materialize a catalog recommendation slot as a normal meal."""

from __future__ import annotations

from uuid import uuid4

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationNotFoundError,
)
from src.domain.model.meal import Meal, MealImage, MealStatus
from src.domain.model.meal_recommendation import (
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.domain.model.nutrition import FoodItem, Macros, Nutrition
from src.domain.utils.timezone_utils import noon_utc_for_date


class RecommendedMealMaterializationService:
    """Build and persist normal meals from immutable catalog recipe snapshots."""

    async def materialize(
        self,
        uow,
        *,
        plan: PersistedMealRecommendationPlan,
        slot: PersistedMealRecommendationSlot,
    ) -> Meal:
        recipe = await uow.catalog_recipes.get_version(slot.recipe_version_id)
        if recipe is None:
            raise MealRecommendationNotFoundError

        food_items = [
            FoodItem(
                id=str(uuid4()),
                name=ingredient.name,
                quantity=ingredient.resolved_grams,
                unit="g",
                macros=Macros(
                    protein=ingredient.protein_g,
                    carbs=ingredient.carbs_g,
                    fat=ingredient.fat_g,
                    fiber=ingredient.fiber_g,
                    sugar=ingredient.sugar_g,
                ),
                food_reference_id=ingredient.food_reference_id,
            )
            for ingredient in recipe.ingredients
            if not ingredient.is_display_only
        ]
        meal_time = noon_utc_for_date(slot.slot_date, plan.timezone)
        meal = Meal(
            meal_id=str(uuid4()),
            user_id=plan.user_id,
            status=MealStatus.READY,
            created_at=meal_time,
            ready_at=meal_time,
            image=MealImage(
                image_id=str(uuid4()),
                format="jpeg",
                size_bytes=1,
                url=None,
            ),
            dish_name=recipe.name,
            nutrition=Nutrition(
                macros=Macros(
                    protein=recipe.protein_g,
                    carbs=recipe.carbs_g,
                    fat=recipe.fat_g,
                    fiber=recipe.fiber_g,
                ),
                food_items=food_items,
            ),
            meal_type=slot.meal_type,
            source="meal_recommendation",
        )
        return await uow.meals.save(meal)
