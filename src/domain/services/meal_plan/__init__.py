"""Meal plan domain services."""
# New consolidated services
from .plan_orchestrator import PlanOrchestrator
from .plan_generator import PlanGenerator
from .meal_plan_formatter import MealPlanFormatter
from .meal_plan_validator import MealPlanValidator, ValidationResult
from .request_builder import RequestBuilder

# Legacy imports (backward compatibility)
from .meal_plan_generator import MealPlanGenerator

__all__ = [
    # New consolidated services
    "PlanOrchestrator",
    "PlanGenerator",
    "MealPlanFormatter",
    "MealPlanValidator",
    "ValidationResult",
    "RequestBuilder",
    # Legacy (deprecated)
    "MealPlanGenerator",
]
