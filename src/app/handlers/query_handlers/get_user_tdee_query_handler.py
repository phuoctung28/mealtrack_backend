"""
GetUserTdeeQueryHandler - Individual handler file.
Auto-extracted for better maintainability.
"""
import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.events.base import EventHandler, handles
from src.app.queries.tdee import GetUserTdeeQuery
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.user import TdeeRequest, Sex, JobType, Goal, UnitSystem, TrainingLevel
from src.domain.services.tdee_service import TdeeCalculationService
from src.infra.database.models.user.profile import UserProfile
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetUserTdeeQuery)
class GetUserTdeeQueryHandler(EventHandler[GetUserTdeeQuery, Dict[str, Any]]):
    """Handler for getting user's TDEE calculation."""

    def __init__(self, tdee_service: TdeeCalculationService = None):
        self.tdee_service = tdee_service or TdeeCalculationService()

    async def handle(self, query: GetUserTdeeQuery) -> Dict[str, Any]:
        """Get user's TDEE calculation based on current profile."""
        with UnitOfWork() as uow:
            # Get current user profile using the UnitOfWork session
            profile = (
                uow.session.query(UserProfile)
                .filter(
                    UserProfile.user_id == query.user_id,
                    UserProfile.is_current.is_(True),
                )
                .first()
            )

            if not profile:
                raise ResourceNotFoundException(f"Current profile for user {query.user_id} not found")

            # Check for custom macro overrides first
            if profile.has_custom_macros:
                return self._build_custom_macros_response(query, profile)

            # Map profile data to TDEE request using centralized mapper
            sex = Sex.MALE if profile.gender.lower() == "male" else Sex.FEMALE

            # Map training level if profile has it
            training_level = None
            if profile.training_level:
                training_level = ActivityGoalMapper.map_training_level(profile.training_level)

            tdee_request = TdeeRequest(
                age=profile.age,
                sex=sex,
                height=profile.height_cm,
                weight=profile.weight_kg,
                job_type=ActivityGoalMapper.map_job_type(profile.job_type),
                training_days_per_week=profile.training_days_per_week,
                training_minutes_per_session=profile.training_minutes_per_session,
                goal=ActivityGoalMapper.map_goal(profile.fitness_goal),
                body_fat_pct=profile.body_fat_percentage,
                unit_system=UnitSystem.METRIC,
                training_level=training_level,
            )

            # Calculate TDEE
            result = self.tdee_service.calculate_tdee(tdee_request)

            # Calculate total multiplier for response
            from src.domain.constants import TDEEConstants
            base_multiplier = TDEEConstants.JOB_TYPE_MULTIPLIERS.get(profile.job_type, 1.2)
            weekly_hours = (profile.training_days_per_week * profile.training_minutes_per_session) / 60.0
            exercise_add = weekly_hours * TDEEConstants.EXERCISE_MULTIPLIER_PER_HOUR
            total_multiplier = base_multiplier + exercise_add

            return {
                "user_id": query.user_id,
                "bmr": result.bmr,
                "tdee": result.tdee,
                "target_calories": round(result.macros.calories, 0),
                "activity_multiplier": round(total_multiplier, 3),
                "formula_used": result.formula_used,
                "is_custom": False,
                "macros": {
                    "protein": round(result.macros.protein, 1),
                    "carbs": round(result.macros.carbs, 1),
                    "fat": round(result.macros.fat, 1),
                    "calories": round(result.macros.calories, 1),
                },
                "profile_data": {
                    "age": profile.age,
                    "gender": profile.gender,
                    "height_cm": profile.height_cm,
                    "weight_kg": profile.weight_kg,
                    "job_type": profile.job_type,
                    "training_days_per_week": profile.training_days_per_week,
                    "training_minutes_per_session": profile.training_minutes_per_session,
                    "fitness_goal": profile.fitness_goal,
                    "body_fat_percentage": profile.body_fat_percentage,
                },
            }

    def _build_custom_macros_response(self, query: GetUserTdeeQuery, profile) -> Dict[str, Any]:
        """Build response using custom macro overrides, still calculating BMR/TDEE for reference."""
        from src.domain.constants import NutritionConstants, TDEEConstants

        custom_calories = (
            profile.custom_protein_g * NutritionConstants.CALORIES_PER_GRAM_PROTEIN
            + profile.custom_carbs_g * NutritionConstants.CALORIES_PER_GRAM_CARBS
            + profile.custom_fat_g * NutritionConstants.CALORIES_PER_GRAM_FAT
        )

        # Still calculate BMR/TDEE for reference display
        sex = Sex.MALE if profile.gender.lower() == "male" else Sex.FEMALE
        training_level = None
        if profile.training_level:
            training_level = ActivityGoalMapper.map_training_level(profile.training_level)

        tdee_request = TdeeRequest(
            age=profile.age,
            sex=sex,
            height=profile.height_cm,
            weight=profile.weight_kg,
            job_type=ActivityGoalMapper.map_job_type(profile.job_type),
            training_days_per_week=profile.training_days_per_week,
            training_minutes_per_session=profile.training_minutes_per_session,
            goal=ActivityGoalMapper.map_goal(profile.fitness_goal),
            body_fat_pct=profile.body_fat_percentage,
            unit_system=UnitSystem.METRIC,
            training_level=training_level,
        )
        result = self.tdee_service.calculate_tdee(tdee_request)

        base_multiplier = TDEEConstants.JOB_TYPE_MULTIPLIERS.get(profile.job_type, 1.2)
        weekly_hours = (profile.training_days_per_week * profile.training_minutes_per_session) / 60.0
        exercise_add = weekly_hours * TDEEConstants.EXERCISE_MULTIPLIER_PER_HOUR
        total_multiplier = base_multiplier + exercise_add

        return {
            "user_id": query.user_id,
            "bmr": result.bmr,
            "tdee": result.tdee,
            "target_calories": round(custom_calories, 0),
            "activity_multiplier": round(total_multiplier, 3),
            "formula_used": result.formula_used,
            "is_custom": True,
            "macros": {
                "protein": round(profile.custom_protein_g, 1),
                "carbs": round(profile.custom_carbs_g, 1),
                "fat": round(profile.custom_fat_g, 1),
                "calories": round(custom_calories, 1),
            },
            "profile_data": {
                "age": profile.age,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "job_type": profile.job_type,
                "training_days_per_week": profile.training_days_per_week,
                "training_minutes_per_session": profile.training_minutes_per_session,
                "fitness_goal": profile.fitness_goal,
                "body_fat_percentage": profile.body_fat_percentage,
            },
        }
