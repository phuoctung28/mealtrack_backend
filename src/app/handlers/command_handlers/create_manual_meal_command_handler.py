"""
Command handler for creating manual meals from selected foods with nutrition data.
All items must provide their own nutrition (via custom_nutrition).
"""
import logging
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

from src.app.commands.meal.create_manual_meal_command import CreateManualMealCommand
from src.app.events.base import EventHandler
from src.app.events.meal.meal_cache_invalidation_required_event import MealCacheInvalidationRequiredEvent
from src.domain.model.meal import Meal, MealStatus
from src.domain.model.meal import MealImage
from src.domain.ports.meal_repository_port import MealRepositoryPort
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now, noon_utc_for_date, resolve_user_timezone_async
from src.domain.services.nutrition_calculation_service import NutritionCalculationService


class CreateManualMealCommandHandler(EventHandler[CreateManualMealCommand, Any]):
    def __init__(self, uow: UnitOfWorkPort, event_bus: Any, meal_repository: Optional[MealRepositoryPort] = None, nutrition_service: Optional[NutritionCalculationService] = None):
        self.uow = uow
        self.event_bus = event_bus
        self.meal_repository = meal_repository
        self.nutrition_service = nutrition_service or NutritionCalculationService()

    async def handle(self, event: CreateManualMealCommand):
        # Use provided meal_repository or create UnitOfWork with context manager
        if self.meal_repository:
            return await self._process_meal(event, self.meal_repository, uow=None)
        else:
            async with self.uow as uow:
                return await self._process_meal(event, uow.meals, uow=uow)

    async def _process_meal(self, event: CreateManualMealCommand, meal_repo, uow=None):
        nutrition, _ = self.nutrition_service.aggregate_from_command_items(event.items)

        # Determine the meal date and datetime
        now = utc_now()
        meal_date = event.target_date if event.target_date else now.date()
        if event.target_date and event.target_date != now.date():
            # Past/future date: use noon in user's local timezone to avoid
            # created_at falling into the wrong date after UTC conversion
            if uow is not None:
                user_tz = await resolve_user_timezone_async(event.user_id, uow)
            else:
                async with self.uow as _uow:
                    user_tz = await resolve_user_timezone_async(event.user_id, _uow)
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

        saved_meal = await meal_repo.save(meal)
        await self.event_bus.publish(MealCacheInvalidationRequiredEvent(
            aggregate_id=event.user_id,
            user_id=event.user_id,
            meal_date=meal_date,
        ))
        return saved_meal
