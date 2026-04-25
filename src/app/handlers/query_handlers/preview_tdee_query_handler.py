"""
Handler - Calculate TPreviewTdeeQueryDEE preview without saving.
"""

import logging
from typing import Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.tdee.preview_tdee_query import PreviewTdeeQuery
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.user import TdeeRequest, Sex, UnitSystem, JobType, TrainingLevel
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


# Job type base multipliers for response
JOB_TYPE_MULTIPLIERS = {
    "desk": 1.2,
    "on_feet": 1.4,
    "physical": 1.6,
}

# Exercise contribution per weekly hour
EXERCISE_MULTIPLIER_PER_HOUR = 0.05


@handles(PreviewTdeeQuery)
class PreviewTdeeQueryHandler(EventHandler[PreviewTdeeQuery, Dict[str, Any]]):
    """Handler for previewing TDEE calculation without persisting."""

    def __init__(self, tdee_service: TdeeCalculationService = None):
        self.tdee_service = tdee_service or TdeeCalculationService()

    async def handle(self, query: PreviewTdeeQuery) -> Dict[str, Any]:
        """Calculate TDEE preview without persisting."""
        # Map inputs using centralized mapper
        sex = Sex.MALE if query.sex.lower() == "male" else Sex.FEMALE
        job_type = JobType(query.job_type)
        goal = ActivityGoalMapper.map_goal(query.goal)
        unit_system = (
            UnitSystem.METRIC if query.unit_system == "metric" else UnitSystem.IMPERIAL
        )

        # Map training level if provided
        training_level = None
        if query.training_level:
            training_level = ActivityGoalMapper.map_training_level(query.training_level)

        # Create TDEE request with new job_type + training fields
        tdee_request = TdeeRequest(
            age=query.age,
            sex=sex,
            height=query.height,
            weight=query.weight,
            job_type=job_type,
            training_days_per_week=query.training_days_per_week,
            training_minutes_per_session=query.training_minutes_per_session,
            goal=goal,
            body_fat_pct=query.body_fat_percentage,
            unit_system=unit_system,
            training_level=training_level,
        )

        # Calculate TDEE
        result = self.tdee_service.calculate_tdee(tdee_request)

        # Calculate activity multiplier for response
        base = JOB_TYPE_MULTIPLIERS.get(job_type.value, 1.2)
        weekly_hours = (
            query.training_days_per_week * query.training_minutes_per_session
        ) / 60.0
        exercise_add = weekly_hours * EXERCISE_MULTIPLIER_PER_HOUR
        activity_multiplier = base + exercise_add

        return {
            "bmr": result.bmr,
            "tdee": result.tdee,
            "goal": goal.value,
            "activity_multiplier": activity_multiplier,
            "formula_used": result.formula_used,
            "macros": {
                "protein": round(result.macros.protein, 1),
                "carbs": round(result.macros.carbs, 1),
                "fat": round(result.macros.fat, 1),
                "calories": round(result.macros.calories, 1),
            },
        }
