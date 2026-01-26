"""
Handler - Calculate TPreviewTdeeQueryDEE preview without saving.
"""
import logging
from typing import Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.tdee.preview_tdee_query import PreviewTdeeQuery
from src.domain.mappers.activity_goal_mapper import ActivityGoalMapper
from src.domain.model.user import TdeeRequest, Sex, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


# Activity multipliers for response
ACTIVITY_MULTIPLIERS = {
    "SEDENTARY": 1.2,
    "LIGHT": 1.375,
    "MODERATE": 1.55,
    "ACTIVE": 1.725,
    "EXTRA": 1.9,
}


@handles(PreviewTdeeQuery)
class PreviewTdeeQueryHandler(EventHandler[PreviewTdeeQuery, Dict[str, Any]]):
    """Handler for previewing TDEE calculation without persisting."""

    def __init__(self, tdee_service: TdeeCalculationService = None):
        self.tdee_service = tdee_service or TdeeCalculationService()

    async def handle(self, query: PreviewTdeeQuery) -> Dict[str, Any]:
        """Calculate TDEE preview without persisting."""
        # Map inputs using centralized mapper
        sex = Sex.MALE if query.sex.lower() == "male" else Sex.FEMALE
        activity_level = ActivityGoalMapper.map_activity_level(query.activity_level)
        goal = ActivityGoalMapper.map_goal(query.goal)
        unit_system = UnitSystem.METRIC if query.unit_system == "metric" else UnitSystem.IMPERIAL

        # Create TDEE request
        tdee_request = TdeeRequest(
            age=query.age,
            sex=sex,
            height=query.height,
            weight=query.weight,
            activity_level=activity_level,
            goal=goal,
            body_fat_pct=query.body_fat_percentage,
            unit_system=unit_system,
        )

        # Calculate TDEE
        result = self.tdee_service.calculate_tdee(tdee_request)

        # Get activity multiplier for response
        activity_multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.name, 1.55)

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
