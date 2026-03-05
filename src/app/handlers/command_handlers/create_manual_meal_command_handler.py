"""
Command handler for creating manual meals from selected foods with nutrition data.
All items must provide their own nutrition (via custom_nutrition).
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.events.base import EventHandler
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal import MealImage
from src.domain.model.nutrition import Macros
from src.domain.model.nutrition import Nutrition, FoodItem as DomainFoodItem
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.utils.timezone_utils import utc_now
from src.infra.cache.cache_service import CacheService
from src.domain.services.nutrition_calculation_service import convert_quantity_to_grams


class CreateManualMealCommandHandler(EventHandler[CreateManualMealCommand, Any]):
    def __init__(self, cache_service: Optional[CacheService] = None, meal_repository: Optional[MealRepositoryPort] = None):
        self.meal_repository = meal_repository
        self.cache_service = cache_service

    async def handle(self, event: CreateManualMealCommand):
        from src.infra.database.uow import UnitOfWork

        # Use provided meal_repository or create UnitOfWork with context manager
        if self.meal_repository:
            return await self._process_meal(event, self.meal_repository)
        else:
            with UnitOfWork() as uow:
                return await self._process_meal(event, uow.meals)

    async def _process_meal(self, event: CreateManualMealCommand, meal_repo):
        # All items must carry their own nutrition (custom_nutrition)
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        food_items: List[DomainFoodItem] = []

        for item in event.items:
            if not item.custom_nutrition:
                # Skip items without nutrition data
                continue

            nutrition = item.custom_nutrition
            quantity = item.quantity
            factor = quantity / 100.0

            calories = nutrition.calories_per_100g * factor
            protein = nutrition.protein_per_100g * factor
            carbs = nutrition.carbs_per_100g * factor
            fat = nutrition.fat_per_100g * factor

            total_calories += calories
            total_protein += protein
            total_carbs += carbs
            total_fat += fat

            food_items.append(
                DomainFoodItem(
                    id=uuid.uuid4(),
                    name=item.name or "Food Item",
                    quantity=quantity,
                    unit=item.unit,
                    calories=calories,
                    macros=Macros(
                        protein=protein,
                        carbs=carbs,
                        fat=fat,
                    ),
                    micros=None,
                    confidence=1.0,
                    fdc_id=item.fdc_id,  # Keep for backward compat
                )
            )

        nutrition = Nutrition(
            calories=round(total_calories, 1),
            macros=Macros(
                protein=round(total_protein, 1),
                carbs=round(total_carbs, 1),
                fat=round(total_fat, 1),
            ),
            food_items=food_items,
            confidence_score=1.0,
        )

        # Determine the meal date - use target_date if provided, otherwise use now
        meal_date = event.target_date if event.target_date else utc_now().date()
        meal_datetime = datetime.combine(meal_date, utc_now().time())
        
        # Determine source: use explicit source if provided, otherwise infer
        source = event.source
        if not source:
            has_custom = any(item.custom_nutrition is not None for item in event.items)
            if has_custom:
                source = "food_search"
            else:
                source = "manual"

        meal = Meal(
            meal_id=str(uuid4()),
            user_id=event.user_id,
            status=MealStatus.READY,
            created_at=meal_datetime,
            image=MealImage(
                image_id=str(uuid4()),
                format="jpeg",
                size_bytes=1,
                url=None,
            ),
            dish_name=event.dish_name,
            nutrition=nutrition,
            ready_at=meal_datetime,
            meal_type=event.meal_type,
            source=source,
        )

        saved_meal = meal_repo.save(meal)
        await self._invalidate_daily_macros(event.user_id, meal_date)
        return saved_meal

    async def _invalidate_daily_macros(self, user_id, target_date):
        if not self.cache_service:
            return
        cache_key, _ = CacheKeys.daily_macros(user_id, target_date)
        await self.cache_service.invalidate(cache_key)
