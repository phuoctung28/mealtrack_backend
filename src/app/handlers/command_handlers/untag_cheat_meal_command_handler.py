"""
Handler for untagging a cheat meal.
"""
import logging
from datetime import date
from typing import Dict, Any, Optional

from src.api.exceptions import ResourceNotFoundException, ValidationException
from src.app.commands.meal import UntagCheatMealCommand
from src.app.events.base import EventHandler, handles
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.meal import MealStatus
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import utc_now, get_user_monday
from src.infra.cache.cache_service import CacheService
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(UntagCheatMealCommand)
class UntagCheatMealCommandHandler(EventHandler[UntagCheatMealCommand, Dict[str, Any]]):
    """Handler for untagging a cheat meal."""

    def __init__(self, uow: Optional[UnitOfWorkPort] = None, cache_service: Optional[CacheService] = None):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, command: UntagCheatMealCommand) -> Dict[str, Any]:
        """Handle untagging a cheat meal (same day only)."""
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

                # Check if meal is actually tagged
                if not meal.is_cheat_meal:
                    raise ValidationException("Meal is not tagged as cheat meal")

                # Same-day enforcement: can only untag on the same calendar day
                if meal.cheat_tagged_at:
                    tagged_date = meal.cheat_tagged_at.date()
                    today = date.today()

                    if tagged_date != today:
                        raise ValidationException(
                            f"Cannot untag meal from a different day. "
                            f"Meal was tagged on {tagged_date}, today is {today}."
                        )

                # Get weekly budget
                meal_date = meal.created_at.date() if meal.created_at else date.today()
                week_start = get_user_monday(meal_date, command.user_id, uow)

                weekly_budget = uow.weekly_budgets.find_by_user_and_week(command.user_id, week_start)

                # Untag the meal
                meal.is_cheat_meal = False
                meal.cheat_tagged_at = None
                uow.meals.save(meal)

                # Release cheat meal
                if weekly_budget:
                    weekly_budget.release_cheat_slot()
                    uow.weekly_budgets.update(weekly_budget)

                uow.commit()

                # Invalidate cache
                await self._invalidate_cache(command.user_id, meal_date, week_start)

                cheat_slots_remaining = weekly_budget.remaining_cheat_slots if weekly_budget else 0

                return {
                    "meal_id": meal.meal_id,
                    "is_cheat_meal": False,
                    "cheat_slots_remaining": cheat_slots_remaining,
                    "message": "Meal untagged from cheat meal"
                }
            except (ResourceNotFoundException, ValidationException):
                uow.rollback()
                raise
            except Exception as e:
                uow.rollback()
                logger.error(f"Error untagging cheat meal: {str(e)}")
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
