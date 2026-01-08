"""Domain services with backward compatibility aliases."""

# Existing services
from .conversation_service import ConversationService
from .daily_meal_suggestion_service import DailyMealSuggestionService
from .meal_plan_service import MealPlanService
from .nutrition_calculation_service import NutritionCalculationService, ScaledNutritionResult
from .portion_calculation_service import PortionCalculationService
from .tdee_service import TdeeCalculationService

# New consolidated services
from .meal import MealCoreService, MealFallbackService
from .suggestion import SuggestionService, SuggestionOrchestrationService
from .meal_plan import PlanOrchestrator, PlanGenerator

# Backward compatibility aliases (deprecated)
from .meal import MealCoreService as MealService
from .meal import MealCoreService as MealTypeDeterminationService
from .suggestion import SuggestionService as MealSuggestionService

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