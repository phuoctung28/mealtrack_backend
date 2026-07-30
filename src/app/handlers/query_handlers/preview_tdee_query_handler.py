"""
Handler - Calculate TPreviewTdeeQueryDEE preview without saving.
"""

import logging
from typing import Any

from src.app.events.base import EventHandler, handles
from src.app.queries.tdee.preview_tdee_query import PreviewTdeeQuery
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.user import (
    JobType,
    MacroPreset,
    MacroTargets,
    Sex,
    TdeeRequest,
    UnitSystem,
)
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


# Job type base multipliers for response
JOB_TYPE_MULTIPLIERS = {
    "desk": 1.2,
    "on_feet": 1.4,
    "physical": 1.6,
}


# Versioned policy identifier shared with onboarding clients.  A preview must
# carry this value so clients can reject a result calculated under another policy.
ONBOARDING_PREVIEW_CALCULATION_CONTRACT = "onboarding_preview_v2"


@handles(PreviewTdeeQuery)
class PreviewTdeeQueryHandler(EventHandler[PreviewTdeeQuery, dict[str, Any]]):
    """Handler for previewing TDEE calculation without persisting."""

    def __init__(self, tdee_service: TdeeCalculationService = None):
        self.tdee_service = tdee_service or TdeeCalculationService()

    async def handle(self, query: PreviewTdeeQuery) -> dict[str, Any]:
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
            macro_preset=MacroPreset.KETO
            if query.diet_type == "keto"
            else MacroPreset.STANDARD,
        )

        # Calculate TDEE
        result = self.tdee_service.calculate_tdee(tdee_request)
        macros = result.macros
        custom_values = [
            query.custom_protein_g,
            query.custom_carbs_g,
            query.custom_fat_g,
        ]
        if all(value is not None for value in custom_values):
            protein, carbs, fat = (round(value, 1) for value in custom_values)
            macros = MacroTargets(
                protein=protein,
                carbs=carbs,
                fat=fat,
                calories=round(protein * 4 + carbs * 4 + fat * 9, 1),
            )
        elif query.requested_calories is not None:
            macros = self.tdee_service.scale_macros(macros, query.requested_calories)

        # Baseline excludes planned workouts; logged movement credits them.
        base = JOB_TYPE_MULTIPLIERS.get(job_type.value, 1.2)

        return {
            "calculation_contract": ONBOARDING_PREVIEW_CALCULATION_CONTRACT,
            "bmr": result.bmr,
            "tdee": result.tdee,
            "goal": goal.value,
            "activity_multiplier": base,
            "formula_used": result.formula_used,
            "macros": {
                "protein": macros.protein,
                "carbs": macros.carbs,
                "fat": macros.fat,
                "calories": macros.calories,
            },
            "macro_preset": result.macro_preset.value,
            "is_custom": any(value is not None for value in custom_values)
            or query.requested_calories is not None,
        }
