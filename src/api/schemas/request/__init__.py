"""
Request DTOs for API endpoints.
"""

# Daily meal requests
from .daily_meal_requests import (
    UserPreferencesRequest,
    MealSuggestionFilterRequest,
    MealTypeEnum
)
# Meal plan requests
from .meal_plan_requests import (
    UserPreferencesSchema,
    ConversationMessageRequest,
    ReplaceMealRequest
)
# Ingredient-based meal plan requests
from .ingredient_based_meal_plan_requests import (
    IngredientBasedMealPlanRequest
)
# Meal requests
from .meal_requests import (
    CreateMealRequest,
    UpdateMealRequest,
    UpdateMealMacrosRequest,
    MealSearchRequest,
    AnalyzeMealImageRequest,
    MacrosRequest
)
# Onboarding requests
from .onboarding_requests import (
    OnboardingCompleteRequest
)
# TDEE requests
from .tdee_requests import (
    TdeeCalculationRequest,
    BatchTdeeCalculationRequest,
    SexEnum,
    ActivityLevelEnum,
    GoalEnum,
    UnitSystemEnum
)

__all__ = [
    # Daily meal
    'UserPreferencesRequest',
    'MealSuggestionFilterRequest',
    'MealTypeEnum',
    
    # Meal
    'CreateMealRequest',
    'UpdateMealRequest',
    'UpdateMealMacrosRequest',
    'MealSearchRequest',
    'AnalyzeMealImageRequest',
    'MacrosRequest',
    
    # TDEE
    'TdeeCalculationRequest',
    'BatchTdeeCalculationRequest',
    'SexEnum',
    'ActivityLevelEnum',
    'GoalEnum',
    'UnitSystemEnum',
    
    # Meal plan
    'UserPreferencesSchema',
    'ConversationMessageRequest',
    'ReplaceMealRequest',
    
    # Ingredient-based meal plan
    'IngredientBasedMealPlanRequest',
    
    # Onboarding
    'OnboardingCompleteRequest'
]