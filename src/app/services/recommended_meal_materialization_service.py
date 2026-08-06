"""Materialize a catalog recommendation slot as a normal meal."""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


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
            logger.warning(
                "materialize.missing_catalog_meal user_id=%s plan_id=%s "
                "slot_id=%s selected_null=%s catalog_meal_id=%s",
                plan.user_id,
                plan.id,
                slot.id,
                slot.selected is None,
                slot.selected.catalog_meal_id if slot.selected is not None else None,
            )
            raise MealRecommendationNotFoundError
        catalog_meal = slot.selected.catalog_meal
        ingredient_count = len(catalog_meal.ingredients)
        logger.info(
            "materialize.start user_id=%s plan_id=%s slot_id=%s "
            "catalog_meal_id=%s ingredients=%s meal_type=%s "
            "slot_date=%s timezone=%s",
            plan.user_id,
            plan.id,
            slot.id,
            catalog_meal.id,
            ingredient_count,
            slot.meal_type,
            slot.slot_date,
            plan.timezone,
        )

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
        saved = await uow.meals.save(meal)
        logger.info(
            "materialize.saved user_id=%s plan_id=%s slot_id=%s meal_id=%s "
            "food_item_count=%s",
            plan.user_id,
            plan.id,
            slot.id,
            saved.meal_id,
            len(food_items),
        )
        return saved
