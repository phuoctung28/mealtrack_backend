"""Materialize a catalog recommendation slot as a normal meal."""

from __future__ import annotations

from uuid import uuid4

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationNotFoundError,
)
from src.domain.model.meal import Meal, MealStatus
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
        if slot.selected is None or slot.selected.catalog_meal is None:
            raise MealRecommendationNotFoundError
        catalog_meal = slot.selected.catalog_meal

        food_items = [
            FoodItem(
                id=str(uuid4()),
                name=ingredient.name,
                quantity=float(ingredient.quantity),
                unit=ingredient.unit,
                macros=Macros(protein=0, carbs=0, fat=0, fiber=0, sugar=0),
                food_reference_id=ingredient.food_reference_id,
            )
            for ingredient in catalog_meal.ingredients
        ]
        meal_time = noon_utc_for_date(slot.slot_date, plan.timezone)
        meal = Meal(
            meal_id=str(uuid4()),
            user_id=plan.user_id,
            status=MealStatus.READY,
            created_at=meal_time,
            ready_at=meal_time,
            image=None,
            dish_name=catalog_meal.name,
            nutrition=Nutrition(
                macros=Macros(
                    protein=float(catalog_meal.protein_g),
                    carbs=float(catalog_meal.carbs_g),
                    fat=float(catalog_meal.fat_g),
                    fiber=float(catalog_meal.fiber_g),
                ),
                food_items=food_items,
            ),
            meal_type=slot.meal_type,
            source="meal_recommendation",
        )
        return await uow.meals.save(meal)
