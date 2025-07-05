"""
Command handlers for TDEE domain - write operations.
"""
import logging
from typing import Dict, Any
from uuid import uuid4

from src.app.commands.tdee import (
    CalculateTdeeCommand
)
from src.app.events.base import EventHandler, handles
from src.app.events.tdee import (
    TdeeCalculatedEvent
)
from src.domain.model.tdee import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


@handles(CalculateTdeeCommand)
class CalculateTdeeCommandHandler(EventHandler[CalculateTdeeCommand, Dict[str, Any]]):
    """Handler for calculating TDEE."""
    
    def __init__(self, tdee_service: TdeeCalculationService = None):
        self.tdee_service = tdee_service or TdeeCalculationService()
    
    def set_dependencies(self, tdee_service: TdeeCalculationService = None):
        """Set dependencies for dependency injection."""
        if tdee_service:
            self.tdee_service = tdee_service
    
    async def handle(self, command: CalculateTdeeCommand) -> Dict[str, Any]:
        """Calculate TDEE based on user parameters."""
        # Map string values to enums
        sex = Sex.MALE if command.sex.lower() == "male" else Sex.FEMALE
        
        activity_map = {
            "sedentary": ActivityLevel.SEDENTARY,
            "lightly_active": ActivityLevel.LIGHT,
            "moderately_active": ActivityLevel.MODERATE,
            "very_active": ActivityLevel.ACTIVE,
            "extra_active": ActivityLevel.EXTRA
        }
        
        goal_map = {
            "lose_weight": Goal.CUTTING,
            "maintain_weight": Goal.MAINTENANCE,
            "gain_weight": Goal.BULKING,
            "build_muscle": Goal.BULKING
        }
        
        # Create TDEE request
        tdee_request = TdeeRequest(
            age=command.age,
            sex=sex,
            height=command.height_cm,
            weight=command.weight_kg,
            activity_level=activity_map.get(command.activity_level, ActivityLevel.MODERATE),
            goal=goal_map.get(command.goal, Goal.MAINTENANCE),
            body_fat_pct=command.body_fat_percentage,
            unit_system=UnitSystem.METRIC if command.unit_system == "metric" else UnitSystem.IMPERIAL
        )
        
        # Calculate TDEE
        result = self.tdee_service.calculate_tdee(tdee_request)
        
        # The service already calculates target calories based on goal
        # and includes macros in the response
        
        # Determine activity multiplier
        activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.EXTRA: 1.9
        }
        activity_multiplier = activity_multipliers.get(tdee_request.activity_level, 1.55)
        
        # Determine formula used
        formula_used = "Katch-McArdle" if tdee_request.body_fat_pct is not None else "Mifflin-St Jeor"
        
        response = {
            "bmr": result.bmr,
            "tdee": result.tdee,
            "target_calories": round(result.macros.calories, 0),
            "activity_multiplier": activity_multiplier,
            "formula_used": formula_used,
            "macros": {
                "protein": round(result.macros.protein, 1),
                "carbs": round(result.macros.carbs, 1),
                "fat": round(result.macros.fat, 1),
                "calories": round(result.macros.calories, 1)
            },
            "events": [
                TdeeCalculatedEvent(
                    aggregate_id=f"user_{str(uuid4())}",
                    user_id=str(uuid4()),
                    bmr=result.bmr,
                    tdee=result.tdee,
                    target_calories=round(result.macros.calories, 0),
                    formula_used=formula_used,
                    calculation_params={
                        "age": command.age,
                        "sex": command.sex,
                        "height_cm": command.height_cm,
                        "weight_kg": command.weight_kg,
                        "activity_level": command.activity_level,
                        "goal": command.goal,
                        "body_fat_percentage": command.body_fat_percentage
                    }
                )
            ]
        }
        
        return response