"""
Query handlers for TDEE domain - read operations.
"""
import logging
from typing import Dict, Any

from src.app.events.base import EventHandler, handles
from src.app.queries.tdee import (
    GetMacroTargetsQuery,
    CompareTdeeMethodsQuery
)
from src.domain.model.tdee import TdeeRequest, Sex, ActivityLevel, Goal, UnitSystem
from src.domain.services.tdee_service import TdeeCalculationService

logger = logging.getLogger(__name__)


@handles(GetMacroTargetsQuery)
class GetMacroTargetsQueryHandler(EventHandler[GetMacroTargetsQuery, Dict[str, Any]]):
    """Handler for calculating macro targets based on TDEE."""
    
    def __init__(self, tdee_service: TdeeCalculationService = None):
        self.tdee_service = tdee_service or TdeeCalculationService()
    
    def set_dependencies(self, tdee_service: TdeeCalculationService = None):
        """Set dependencies for dependency injection."""
        if tdee_service:
            self.tdee_service = tdee_service
    
    async def handle(self, query: GetMacroTargetsQuery) -> Dict[str, Any]:
        """Calculate macro targets based on TDEE and goal."""
        goal_map = {
            "lose_weight": Goal.CUTTING,
            "maintain_weight": Goal.MAINTENANCE,
            "gain_weight": Goal.BULKING,
            "build_muscle": Goal.BULKING
        }
        
        goal = goal_map.get(query.goal, Goal.MAINTENANCE)
        
        # Calculate macros
        macros = self.tdee_service.calculate_macros(
            tdee=query.tdee,
            goal=goal,
            weight_kg=query.weight_kg
        )
        
        return {
            "protein": round(macros.protein, 1),
            "carbs": round(macros.carbs, 1),
            "fat": round(macros.fat, 1),
            "calories": round(macros.calories, 1)
        }


@handles(CompareTdeeMethodsQuery)
class CompareTdeeMethodsQueryHandler(EventHandler[CompareTdeeMethodsQuery, Dict[str, Any]]):
    """Handler for comparing different TDEE calculation methods."""
    
    def __init__(self, tdee_service: TdeeCalculationService = None):
        self.tdee_service = tdee_service or TdeeCalculationService()
    
    def set_dependencies(self, tdee_service: TdeeCalculationService = None):
        """Set dependencies for dependency injection."""
        if tdee_service:
            self.tdee_service = tdee_service
    
    async def handle(self, query: CompareTdeeMethodsQuery) -> Dict[str, Any]:
        """Compare different TDEE calculation methods."""
        # Map string values to enums
        sex = Sex.MALE if query.sex.lower() == "male" else Sex.FEMALE
        
        activity_map = {
            "sedentary": ActivityLevel.SEDENTARY,
            "lightly_active": ActivityLevel.LIGHT,
            "moderately_active": ActivityLevel.MODERATE,
            "very_active": ActivityLevel.ACTIVE,
            "extra_active": ActivityLevel.EXTRA
        }
        
        # Create TDEE request
        tdee_request = TdeeRequest(
            age=query.age,
            sex=sex,
            height_cm=query.height_cm,
            weight_kg=query.weight_kg,
            activity_level=activity_map.get(query.activity_level, ActivityLevel.MODERATE),
            goal=Goal.MAINTENANCE,  # Use maintenance for comparison
            body_fat_percentage=query.body_fat_percentage,
            unit_system=UnitSystem.METRIC
        )
        
        # Calculate with different formulas
        results = {}
        
        # Mifflin-St Jeor (standard formula)
        mifflin_result = self.tdee_service.calculate_tdee(tdee_request)
        results["mifflin_st_jeor"] = {
            "bmr": mifflin_result.bmr,
            "tdee": mifflin_result.tdee
        }
        
        # Harris-Benedict (older formula)
        # Note: In a real implementation, you would have different calculation methods
        harris_bmr = self._calculate_harris_benedict_bmr(
            query.age, sex, query.height_cm, query.weight_kg
        )
        harris_tdee = harris_bmr * mifflin_result.activity_multiplier
        results["harris_benedict"] = {
            "bmr": harris_bmr,
            "tdee": harris_tdee
        }
        
        # Katch-McArdle (if body fat provided)
        if query.body_fat_percentage:
            katch_result = self.tdee_service.calculate_tdee(tdee_request)
            results["katch_mcardle"] = {
                "bmr": katch_result.bmr,
                "tdee": katch_result.tdee
            }
        
        # Calculate average
        tdee_values = [r["tdee"] for r in results.values()]
        average_tdee = sum(tdee_values) / len(tdee_values)
        
        # Recommendation
        if query.body_fat_percentage:
            recommendation = "Katch-McArdle formula is recommended as you provided body fat percentage"
        else:
            recommendation = "Mifflin-St Jeor formula is recommended as the most accurate modern formula"
        
        return {
            **results,
            "average_tdee": round(average_tdee, 0),
            "recommendation": recommendation
        }
    
    def _calculate_harris_benedict_bmr(self, age: int, sex: Sex, height_cm: float, weight_kg: float) -> float:
        """Calculate BMR using Harris-Benedict formula."""
        if sex == Sex.MALE:
            bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
        return round(bmr, 0)