"""
TDEE calculation helpers for SuggestionOrchestrationService.
Builds TdeeRequest from user profile and fetches adjusted daily target from weekly budget.
"""
import logging
from datetime import date
from typing import Any

from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.user import TdeeRequest, Sex, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService
from src.domain.services.weekly_budget_service import WeeklyBudgetService
from src.domain.utils.timezone_utils import get_user_monday

logger = logging.getLogger(__name__)


def build_tdee_request(profile: Any) -> TdeeRequest:
    """Build a TdeeRequest from a user profile domain object."""
    gender = profile.gender or "male"
    sex = Sex.MALE if gender.lower() == "male" else Sex.FEMALE
    return TdeeRequest(
        age=profile.age,
        sex=sex,
        height=profile.height_cm,
        weight=profile.weight_kg,
        job_type=ActivityGoalMapper.map_job_type(profile.job_type),
        training_days_per_week=profile.training_days_per_week,
        training_minutes_per_session=profile.training_minutes_per_session,
        training_level=ActivityGoalMapper.map_training_level(profile.training_level),
        goal=ActivityGoalMapper.map_goal(profile.fitness_goal),
        body_fat_pct=profile.body_fat_percentage,
        unit_system=UnitSystem.METRIC,
    )


def calculate_daily_tdee(tdee_service: TdeeCalculationService, profile: Any) -> float:
    """Calculate raw daily TDEE calories from profile. Returns 2000 on failure."""
    try:
        return tdee_service.calculate_tdee(build_tdee_request(profile)).macros.calories
    except Exception as e:
        logger.warning(f"Failed to calculate TDEE: {e}. Using default 2000 calories.")
        return 2000.0


async def get_adjusted_daily_target(
    tdee_service: TdeeCalculationService, user_id: str, profile: Any, uow: Any = None
) -> float:
    """Return adjusted daily calorie target using Skip & Redistribute.

    Delegates to WeeklyBudgetService.get_effective_adjusted_daily() which
    recalculates consumed from actual meals (not stale DB values).
    Falls back to raw TDEE if no budget exists or uow not provided.
    """
    try:
        tdee_result = tdee_service.calculate_tdee(build_tdee_request(profile))
        base_calories = tdee_result.macros.calories
        bmr = tdee_result.bmr

        if uow is None:
            logger.info(f"No UoW provided for user {user_id}, using raw TDEE: {base_calories}")
            return base_calories

        from src.domain.utils.timezone_utils import resolve_user_timezone, user_today
        user_tz = resolve_user_timezone(user_id, uow)
        today = user_today(user_tz)
        week_start = get_user_monday(today, user_id, uow)
        weekly_budget = uow.weekly_budgets.find_by_user_and_week(user_id, week_start)

        if not weekly_budget:
            logger.info(f"No weekly budget for user {user_id}, using raw TDEE: {base_calories}")
            return base_calories

        # Use shared method: recalculates consumed, applies skip/redistribute
        effective = WeeklyBudgetService.get_effective_adjusted_daily(
            uow=uow, user_id=user_id,
            week_start=week_start, target_date=today,
            weekly_budget=weekly_budget,
            base_daily_cal=base_calories,
            base_daily_protein=tdee_result.macros.protein,
            base_daily_carbs=tdee_result.macros.carbs,
            base_daily_fat=tdee_result.macros.fat,
            bmr=bmr, user_timezone=user_tz,
        )
        logger.info(
            f"Adjusted daily target for user {user_id}: "
            f"{effective.adjusted.calories:.0f} kcal (base: {base_calories:.0f}, "
            f"bmr_floor: {effective.adjusted.bmr_floor_active})"
        )
        return effective.adjusted.calories

    except Exception as e:
        logger.warning(f"Failed to get adjusted daily target: {e}. Falling back to raw TDEE.")
        return calculate_daily_tdee(tdee_service, profile)
