"""
Daily ingredient-based meal plan service.
Uses the unified orchestration service.
"""
import logging
from typing import Dict, Any

from src.domain.model.meal_generation_response import DailyMealPlan
from src.domain.services.meal_plan_orchestration_service import MealPlanOrchestrationService
from src.infra.adapters.meal_generation_service import MealGenerationService

logger = logging.getLogger(__name__)


class IngredientBasedMealPlanService:
    """Service for generating daily ingredient-based meal plans."""
    
    def __init__(self):
        meal_generation_service = MealGenerationService()
        self.orchestration_service = MealPlanOrchestrationService(meal_generation_service)
    
    def generate_ingredient_based_meal_plan(self, request_data: Dict[str, Any]) -> DailyMealPlan:
        """Generate daily ingredient-based meal plan using orchestration service."""
        return self.orchestration_service.generate_daily_ingredient_based_plan(request_data)