"""
Request DTOs for API endpoints.
"""

# Activity requests
from .activity_requests import (
    ActivityFilterRequest
)
# Daily meal requests
from .daily_meal_requests import (
    UserPreferencesRequest,
    MealSuggestionFilterRequest,
    MealTypeEnum
)
# Ingredient requests
from .ingredient_requests import (
    CreateIngredientRequest,
    UpdateIngredientRequest
)
# Macros requests
from .macros_requests import (
    OnboardingChoicesRequest,
    ConsumedMacrosRequest
)
# Meal plan requests
from .meal_plan_requests import (
    UserPreferencesSchema,
    ConversationMessageRequest,
    ReplaceMealRequest,
    GenerateMealPlanRequest
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
    OnboardingResponseRequest,
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
    
    # Activity
    'ActivityFilterRequest',
    
    # Macros
    'OnboardingChoicesRequest',
    'ConsumedMacrosRequest',
    
    # Ingredient
    'CreateIngredientRequest',
    'UpdateIngredientRequest',
    
    # Meal plan
    'UserPreferencesSchema',
    'ConversationMessageRequest',
    'ReplaceMealRequest',
    'GenerateMealPlanRequest',
    
    # Onboarding
    'OnboardingResponseRequest',
    'OnboardingCompleteRequest'
]