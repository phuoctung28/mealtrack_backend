"""
SaveMealSuggestionCommandHandler - Handler for saving meal suggestions as regular meals.
"""
import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional

from src.app.commands.meal_suggestion import SaveMealSuggestionCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model import Meal, MealStatus, MealImage, Nutrition, Macros
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

    This creates a Meal domain entity with basic nutrition data derived from the
    suggestion and saves it via the MealRepository. It also invalidates the
    user's daily macros cache for the target date if a cache service is provided.
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

        # Build minimal nutrition from suggestion macros
        macros = Macros(
            protein=command.protein,
            carbs=command.carbs,
            fat=command.fat,
        )
        nutrition = Nutrition(
            calories=command.calories,
            macros=macros,
            food_items=None,
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

    async def _invalidate_daily_macros(self, user_id: str, target_date) -> None:
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.invalidate(cache_key)

