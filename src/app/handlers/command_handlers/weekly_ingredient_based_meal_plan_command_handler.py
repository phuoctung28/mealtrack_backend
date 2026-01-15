"""
Command handler for weekly ingredient-based meal-plan generation.
Works with Python 3.11 and the simplified WeeklyIngredientBasedMealPlanService.
"""

import logging
from typing import Any, Dict

from src.app.commands.meal_plan import GenerateWeeklyIngredientBasedMealPlanCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.meal_planning import PlanDuration
from src.infra.services.meal_plan_persistence_service import MealPlanPersistenceService
from src.domain.services.user_profile_service import UserProfileService
from src.domain.services.weekly_ingredient_based_meal_plan_service import (
    WeeklyIngredientBasedMealPlanService,
)
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.adapters.meal_generation_service import MealGenerationService
from src.infra.database.config import ScopedSession
from src.infra.repositories.user_repository import UserRepository
from src.domain.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


@handles(GenerateWeeklyIngredientBasedMealPlanCommand)
class GenerateWeeklyIngredientBasedMealPlanCommandHandler(
    EventHandler[GenerateWeeklyIngredientBasedMealPlanCommand, Dict[str, Any]]
):
    """Generate and persist a Monday-to-Sunday meal plan."""

    def __init__(self) -> None:
        meal_generation_service = MealGenerationService()
        self.meal_plan_service = WeeklyIngredientBasedMealPlanService(meal_generation_service)

    # ------------------------------------------------------------------ #
    # main handler                                                       #
    # ------------------------------------------------------------------ #

    async def handle(
        self, command: GenerateWeeklyIngredientBasedMealPlanCommand
    ) -> Dict[str, Any]:
        db = ScopedSession()
        
        # Instantiate services with dependencies
        user_repo = UserRepository(db)
        tdee_service = TdeeCalculationService()
        user_profile_service = UserProfileService(user_repo, tdee_service)
        
        persistence_service = MealPlanPersistenceService(db)

        logger.info(
            "Generating weekly ingredient-based meal plan for user %s (%d ingredients)",
            command.user_id,
            len(command.available_ingredients),
        )

        # ── 1. get user profile data using shared service ──────────────
        user_data = await user_profile_service.get_user_profile_or_defaults(command.user_id)
        
        # ── 2. calculate next Monday-Sunday dates ───────────────────────
        from datetime import datetime, timedelta
        today = utc_now().date()
        days_since_monday = today.weekday()  # Monday = 0
        # Calculate next Monday
        days_until_next_monday = 7 - days_since_monday if days_since_monday != 0 else 7
        start_date = today + timedelta(days=days_until_next_monday)
        end_date = start_date + timedelta(days=6)
        
        # ── 3. prepare request data with specific dates ─────────────────
        request_data = {
            "user_id": command.user_id,
            "available_ingredients": command.available_ingredients,
            "available_seasonings": command.available_seasonings,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "start_date_obj": start_date,
            "end_date_obj": end_date,
            **user_data  # Include all user profile data
        }

        try:
            plan_json = self.meal_plan_service.generate_weekly_meal_plan(request_data)
        except Exception as exc:  # pragma: no cover
            logger.exception("Meal-plan generation failed")
            raise

        logger.info("Meal plan generated for user %s", command.user_id)

        # ── 3. persist meal plan using shared service ───────────────────
        user_preferences = user_profile_service.create_user_preferences_from_data(
            user_data, PlanDuration.WEEKLY
        )
        plan_id = persistence_service.save_weekly_meal_plan(
            plan_json, user_preferences, command.user_id
        )
        plan_json["plan_id"] = plan_id

        return plan_json