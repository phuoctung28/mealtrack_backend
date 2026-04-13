"""Domain services with backward compatibility aliases."""

# Existing services
from .daily_meal_suggestion_service import DailyMealSuggestionService
# New consolidated services
from .meal import MealCoreService, MealFallbackService
# Backward compatibility aliases (deprecated)
from .meal import MealCoreService as MealService
from .meal import MealCoreService as MealTypeDeterminationService
from .nutrition_calculation_service import NutritionCalculationService, ScaledNutritionResult
from .portion_calculation_service import PortionCalculationService
from .suggestion import SuggestionService, SuggestionOrchestrationService
from .suggestion import SuggestionService as MealSuggestionService
from .tdee_service import TdeeCalculationService

__all__ = [
    # Existing services
    "TdeeCalculationService",
    "DailyMealSuggestionService",
    "NutritionCalculationService",
    "ScaledNutritionResult",
    "PortionCalculationService",
    # New consolidated services
    "MealCoreService",
    "MealFallbackService",
    "SuggestionService",
    "SuggestionOrchestrationService",
    # Backward compatibility (deprecated)
    "MealService",
    "MealTypeDeterminationService",
    "MealSuggestionService",
] 