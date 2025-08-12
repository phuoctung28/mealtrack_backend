"""
Weekly ingredient-based meal plan service.
Uses the unified orchestration service.
"""
import logging
from typing import Any, Dict

from src.domain.services.meal_plan_orchestration_service import MealPlanOrchestrationService
from src.infra.adapters.meal_generation_service import MealGenerationService

logger = logging.getLogger(__name__)


class WeeklyIngredientBasedMealPlanService:
    """
    Service for generating weekly ingredient-based meal plans.
    Delegates to unified orchestration service.
    """

    def __init__(self) -> None:
        meal_generation_service = MealGenerationService()
        self.orchestration_service = MealPlanOrchestrationService(meal_generation_service)

    def generate_weekly_meal_plan(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate weekly meal plan using orchestration service."""
        return self.orchestration_service.generate_weekly_ingredient_based_plan(request)