"""
Handler for tagging a meal as a cheat meal.
"""
import logging
from datetime import date
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.meal import TagCheatMealCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import MealStatus
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now, get_user_monday
from src.domain.constants import WeeklyBudgetConstants
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(TagCheatMealCommand)
class TagCheatMealCommandHandler(EventHandler[TagCheatMealCommand, Dict[str, Any]]):
    """Handler for tagging a meal as a cheat meal."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None, cache_service: Optional[CacheService] = None):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: TagCheatMealCommand) -> Dict[str, Any]:
        """Handle tagging a meal as cheat meal."""
        uow = self.uow or UnitOfWork()

        with uow:
            try:
                # Get meal
                meal = uow.meals.find_by_id(command.meal_id)
                if not meal:
                    raise ResourceNotFoundException(f"Meal with ID {command.meal_id} not found")

                # Verify meal belongs to user
                if meal.user_id != command.user_id:
                    raise ValidationException("Meal does not belong to user")

                # Check meal is ready
                if meal.status != MealStatus.READY:
                    raise ValidationException("Only ready meals can be tagged as cheat")

                # Check if already tagged
                if meal.is_cheat_meal:
                    raise ValidationException("Meal is already tagged as cheat meal")

                # Get or create weekly budget
                meal_date = meal.created_at.date() if meal.created_at else date.today()
                week_start = get_user_monday(meal_date, command.user_id, uow)

                # Load or create weekly budget
                weekly_budget = uow.weekly_budgets.find_by_user_and_week(command.user_id, week_start)

                if not weekly_budget:
                    raise ValidationException("Weekly budget not found. Please log a meal first.")

                # Check cheat slots remaining
                if weekly_budget.remaining_cheat_slots <= 0:
                    raise ValidationException("No cheat meal slots remaining for this week")

                # Tag the meal
                now = utc_now()
                meal.is_cheat_meal = True
                meal.cheat_tagged_at = now
                uow.meals.save(meal)

                # Use cheat slot
                weekly_budget.use_cheat_slot()
                uow.weekly_budgets.update(weekly_budget)

                uow.commit()

                # Invalidate cache
                await self._invalidate_cache(command.user_id, meal_date, week_start)

                return {
                    "meal_id": meal.meal_id,
                    "is_cheat_meal": True,
                    "cheat_slots_remaining": weekly_budget.remaining_cheat_slots,
                    "message": "Meal tagged as cheat meal"
                }
            except (ResourceNotFoundException, ValidationException):
                uow.rollback()
                raise
            except Exception as e:
                uow.rollback()
                logger.error(f"Error tagging cheat meal: {str(e)}")
                raise

    async def _invalidate_cache(self, user_id: str, meal_date: date, week_start: date):
        if not self.cache_service:
            return

        # Invalidate daily macros cache
        daily_key, _ = CacheKeys.daily_macros(user_id, meal_date)
        await self.cache_service.invalidate(daily_key)

        # Invalidate weekly budget cache
        weekly_key, _ = CacheKeys.weekly_budget(user_id, week_start)
        await self.cache_service.invalidate(weekly_key)
