"""
Command handler for creating manual meals from selected foods with nutrition data.
All items must provide their own nutrition (via custom_nutrition).
"""
import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.events.base import EventHandler
from src.app.events.meal.meal_cache_invalidation_required_event import MealCacheInvalidationRequiredEvent
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal import MealImage
from src.domain.model.nutrition import Macros
from src.domain.model.nutrition import Nutrition, FoodItem as DomainFoodItem
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now, noon_utc_for_date, resolve_user_timezone
from src.domain.services.nutrition_calculation_service import convert_quantity_to_grams


class CreateManualMealCommandHandler(EventHandler[CreateManualMealCommand, Any]):
    def __init__(self, uow: UnitOfWorkPort, event_bus: Any, meal_repository: Optional[MealRepositoryPort] = None):
        self.uow = uow
        self.event_bus = event_bus
        self.meal_repository = meal_repository

    async def handle(self, event: CreateManualMealCommand):
        # Use provided meal_repository or create UnitOfWork with context manager
        if self.meal_repository:
            return await self._process_meal(event, self.meal_repository, uow=None)
        else:
            with self.uow as uow:
                return await self._process_meal(event, uow.meals, uow=uow)

    async def _process_meal(self, event: CreateManualMealCommand, meal_repo, uow=None):
        # All items must carry their own nutrition (custom_nutrition)
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

            protein = nutrition.protein_per_100g * factor
            carbs = nutrition.carbs_per_100g * factor
            fat = nutrition.fat_per_100g * factor

            total_protein += protein
            total_carbs += carbs
            total_fat += fat

            food_items.append(
                DomainFoodItem(
                    id=uuid.uuid4(),
                    name=item.name or "Food Item",
                    quantity=quantity,
                    unit=item.unit,
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
            macros=Macros(
                protein=round(total_protein, 1),
                carbs=round(total_carbs, 1),
                fat=round(total_fat, 1),
            ),
            food_items=food_items,
            confidence_score=1.0,
        )

        # Determine the meal date and datetime
        now = utc_now()
        meal_date = event.target_date if event.target_date else now.date()
        if event.target_date and event.target_date != now.date():
            # Past/future date: use noon in user's local timezone to avoid
            # created_at falling into the wrong date after UTC conversion
            if uow is not None:
                user_tz = resolve_user_timezone(event.user_id, uow)
            else:
                with self.uow as _uow:
                    user_tz = resolve_user_timezone(event.user_id, _uow)
            meal_datetime = noon_utc_for_date(meal_date, user_tz)
        else:
            # Today or no date — use actual current time
            meal_datetime = now
        
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
            emoji=event.emoji,
            nutrition=nutrition,
            ready_at=meal_datetime,
            meal_type=event.meal_type,
            source=source,
        )

        saved_meal = meal_repo.save(meal)
        await self.event_bus.publish(MealCacheInvalidationRequiredEvent(
            aggregate_id=event.user_id,
            user_id=event.user_id,
            meal_date=meal_date,
        ))
        return saved_meal
