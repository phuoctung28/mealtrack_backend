"""
SaveMealSuggestionCommandHandler - Handler for saving meal suggestions as regular meals.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from src.app.commands.meal_suggestion import IngredientItem, SaveMealSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model import FoodItem, Meal, MealImage, MealStatus, Nutrition, Macros
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(SaveMealSuggestionCommand)
class SaveMealSuggestionCommandHandler(
    EventHandler[SaveMealSuggestionCommand, str]
):
    """
    Handler for saving meal suggestions as regular meals.

    Creates a Meal domain entity populated with structured FoodItem objects built
    from the suggestion's ingredient list (name/amount/unit). Per-item calories and
    macros are set to zero because the AI only provides meal-level totals; the
    meal-level Nutrition carries the accurate aggregated values.
    """

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache_service = cache_service

    async def handle(self, command: SaveMealSuggestionCommand) -> str:
        """
        Save meal suggestion as a regular meal in the meals table.

        Args:
            command: SaveMealSuggestionCommand with meal suggestion data

        Returns:
            meal_id: ID of the created meal
        """
        # Parse target meal date
        meal_date = datetime.strptime(command.meal_date, "%Y-%m-%d").date()
        now = utc_now()
        meal_datetime = datetime.combine(meal_date, now.timetz())

        # Build nutrition: total macros from suggestion, food items from ingredient list
        macros = Macros(
            protein=command.protein,
            carbs=command.carbs,
            fat=command.fat,
        )
        food_items = self._build_food_items(command.ingredients)
        nutrition = Nutrition(
            calories=command.calories,
            macros=macros,
            food_items=food_items if food_items else None,
            confidence_score=1.0,
        )

        # Create a dummy image reference (no actual upload)
        image = MealImage(
            image_id=str(uuid4()),
            format="jpeg",
            size_bytes=1,
            url=None,
        )

        meal = Meal(
            meal_id=str(uuid4()),
            user_id=command.user_id,
            status=MealStatus.READY,
            created_at=meal_datetime,
            image=image,
            dish_name=command.name,
            nutrition=nutrition,
            ready_at=meal_datetime,
            error_message=None,
            raw_gpt_json=None,
            updated_at=meal_datetime,
            last_edited_at=None,
            edit_count=0,
            is_manually_edited=False,
            meal_type=command.meal_type,
            translations=None,
            source='ai_suggestion',
        )

        with UnitOfWork() as uow:
            saved_meal = uow.meals.save(meal)

            # Invalidate daily macros cache for this user/date if cache is configured
            await self._invalidate_daily_macros(command.user_id, meal_date)

            logger.info(
                f"Saved meal suggestion {command.suggestion_id} as meal {saved_meal.meal_id} "
                f"for user {command.user_id} on {meal_date} "
                f"({command.portion_multiplier}x servings, {command.calories} cal)"
            )

            return saved_meal.meal_id

    @staticmethod
    def _build_food_items(ingredients: List[IngredientItem]) -> List[FoodItem]:
        """
        Convert suggestion ingredients into FoodItem domain objects.

        Uses per-ingredient macros when provided by the caller. Falls back to
        zero values when unavailable (e.g. saving directly from an AI suggestion
        without a nutrition DB lookup). The meal-level Nutrition object always
        carries the accurate aggregated totals regardless.
        """
        items = []
        for ingredient in ingredients:
            try:
                items.append(
                    FoodItem(
                        id=str(uuid4()),
                        name=ingredient.name,
                        quantity=ingredient.amount,
                        unit=ingredient.unit,
                        calories=ingredient.calories,
                        macros=Macros(
                            protein=ingredient.protein,
                            carbs=ingredient.carbs,
                            fat=ingredient.fat,
                        ),
                        confidence=1.0,
                        is_custom=True,
                    )
                )
            except ValueError as exc:
                logger.warning(
                    "Skipping invalid ingredient %r: %s", ingredient.name, exc
                )
        return items

    async def _invalidate_daily_macros(self, user_id: str, target_date) -> None:
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.invalidate(cache_key)

