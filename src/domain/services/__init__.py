"""Domain services with backward compatibility aliases."""

# New consolidated services
from .nutrition_calculation_service import (
    NutritionCalculationService,
    ScaledNutritionResult,
)
from .portion_calculation_service import PortionCalculationService
from .suggestion import SuggestionService, SuggestionOrchestrationService
from .suggestion import SuggestionService as MealSuggestionService
from .tdee_service import TdeeCalculationService

__all__ = [
    # Existing services
    "TdeeCalculationService",
    "NutritionCalculationService",
    "ScaledNutritionResult",
    "PortionCalculationService",
    # New consolidated services
    "SuggestionService",
    "SuggestionOrchestrationService",
    # Backward compatibility (deprecated)
    "MealSuggestionService",
]
