"""Materialize a catalog recommendation slot as a normal meal."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from src.domain.exceptions.meal_recommendation_exceptions import (
    MealRecommendationNotFoundError,
)
from src.domain.model.meal import Meal, MealImage, MealStatus
from src.domain.model.meal_recommendation import (
    CatalogMeal,
    PersistedMealRecommendationPlan,
    PersistedMealRecommendationSlot,
)
from src.domain.model.nutrition import FoodItem, Macros, Nutrition
from src.domain.utils.timezone_utils import noon_utc_for_date

# mealimage.url is VARCHAR(255); keep inserts valid when catalog URLs are longer.
_MEAL_IMAGE_URL_MAX_LEN = 255


class RecommendedMealMaterializationService:
    """Build and persist normal meals from immutable catalog recipe snapshots."""

    async def materialize(
        self,
        uow,
        *,
        plan: PersistedMealRecommendationPlan,
        slot: PersistedMealRecommendationSlot,
        meal_date: date | None = None,
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
        meal_time = noon_utc_for_date(meal_date or slot.slot_date, plan.timezone)
        # Always attach a MealImage row. Production still enforces NOT NULL on
        # meal.image_id in some environments; image-less inserts 500 there.
        # Matches manual / AI-suggestion materialization (placeholder image).
        meal = Meal(
            meal_id=str(uuid4()),
            user_id=plan.user_id,
            status=MealStatus.READY,
            created_at=meal_time,
            ready_at=meal_time,
            image=_meal_image_for_catalog(catalog_meal),
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


def _meal_image_for_catalog(catalog_meal: CatalogMeal) -> MealImage:
    """Build a mealimage row from catalog URL, or a placeholder when absent."""

    raw_url = (catalog_meal.image_url or "").strip() or None
    url = raw_url if raw_url and len(raw_url) <= _MEAL_IMAGE_URL_MAX_LEN else None
    return MealImage(
        image_id=str(uuid4()),
        format="jpeg",
        size_bytes=1,
        url=url,
    )
