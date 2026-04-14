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
from src.domain.utils.timezone_utils import utc_now, noon_utc_for_date, resolve_user_timezone
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
        now = utc_now()
        meal_date = datetime.strptime(command.meal_date, "%Y-%m-%d").date()
        if meal_date != now.date():
            # Past/future date: use noon to avoid date-boundary issues
            with UnitOfWork() as uow:
                user_tz = resolve_user_timezone(command.user_id, uow)
            meal_datetime = noon_utc_for_date(meal_date, user_tz)
        else:
            # Today — use actual current time
            meal_datetime = now

        # Build nutrition: total macros from suggestion, food items from ingredient list
        macros = Macros(
            protein=command.protein,
            carbs=command.carbs,
            fat=command.fat,
        )
        food_items = self._build_food_items(
            command.ingredients,
            total_protein=command.protein,
            total_carbs=command.carbs,
            total_fat=command.fat,
        )
        nutrition = Nutrition(
            macros=macros,
            food_items=food_items if food_items else None,
            confidence_score=1.0,
        )

        # Image reference: use discovery image URL if provided, else placeholder
        image = MealImage(
            image_id=str(uuid4()),
            format="jpeg",
            size_bytes=1,
            url=command.image_url,
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
            description=command.description,
            instructions=command.instructions if command.instructions else None,
            cook_time_min=command.estimated_cook_time_minutes,
            cuisine_type=command.cuisine_type,
            origin_country=command.origin_country,
            emoji=command.emoji,
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

    def _build_food_items(
        self,
        ingredients: List[IngredientItem],
        total_protein: float,
        total_carbs: float,
        total_fat: float,
    ) -> List[FoodItem]:
        """
        Convert suggestion ingredients into FoodItem domain objects.

        Uses per-ingredient macros when provided. If all items have zero
        macros but meal-level totals exist, distributes totals
        proportionally by estimated weight.
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

        # Distribute meal-level totals when all items have 0 calories (derived from macros)
        if items and total_protein + total_carbs + total_fat > 0 and all(
            item.macros.protein == 0 and item.macros.carbs == 0 and item.macros.fat == 0
            for item in items
        ):
            items = self._distribute_nutrition(
                items, total_protein, total_carbs, total_fat
            )

        return items

    @staticmethod
    def _estimate_weight_grams(quantity: float, unit: str) -> float:
        """Estimate weight in grams for proportional distribution."""
        conversions = {
            'g': 1.0, 'kg': 1000.0, 'oz': 28.35, 'lb': 453.6,
            'ml': 1.0, 'l': 1000.0, 'cup': 240.0, 'tbsp': 15.0, 'tsp': 5.0,
        }
        return quantity * conversions.get(unit.lower().strip(), 1.0)

    def _distribute_nutrition(
        self,
        items: List[FoodItem],
        total_protein: float,
        total_carbs: float,
        total_fat: float,
    ) -> List[FoodItem]:
        """Distribute meal-level macro totals proportionally by estimated weight."""
        total_weight = sum(
            self._estimate_weight_grams(item.quantity, item.unit) for item in items
        )
        if total_weight <= 0:
            return items

        distributed = []
        for item in items:
            ratio = self._estimate_weight_grams(item.quantity, item.unit) / total_weight
            distributed.append(FoodItem(
                id=item.id,
                name=item.name,
                quantity=item.quantity,
                unit=item.unit,
                macros=Macros(
                    protein=round(total_protein * ratio, 1),
                    carbs=round(total_carbs * ratio, 1),
                    fat=round(total_fat * ratio, 1),
                ),
                confidence=0.8,
                is_custom=True,
            ))
        return distributed

    async def _invalidate_daily_macros(self, user_id: str, target_date) -> None:
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.invalidate(cache_key)

