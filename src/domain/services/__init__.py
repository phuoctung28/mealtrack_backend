"""Domain services with backward compatibility aliases."""

# Existing services
from .conversation_service import ConversationService
from .daily_meal_suggestion_service import DailyMealSuggestionService
# New consolidated services
from .meal import MealCoreService, MealFallbackService
# Backward compatibility aliases (deprecated)
from .meal import MealCoreService as MealService
from .meal import MealCoreService as MealTypeDeterminationService
from .meal_plan import PlanOrchestrator, PlanGenerator
from .meal_plan_service import MealPlanService
from .nutrition_calculation_service import NutritionCalculationService, ScaledNutritionResult
from .portion_calculation_service import PortionCalculationService
from .suggestion import SuggestionService, SuggestionOrchestrationService
from .suggestion import SuggestionService as MealSuggestionService
from .tdee_service import TdeeCalculationService

__all__ = [
    # Existing services
    "TdeeCalculationService",
    "MealPlanService",
    "ConversationService",
    "DailyMealSuggestionService",
    "NutritionCalculationService",
    "ScaledNutritionResult",
    "PortionCalculationService",
    # New consolidated services
    "MealCoreService",
    "MealFallbackService",
    "SuggestionService",
    "SuggestionOrchestrationService",
    "PlanOrchestrator",
    "PlanGenerator",
    # Backward compatibility (deprecated)
    "MealService",
    "MealTypeDeterminationService",
    "MealSuggestionService",
] 