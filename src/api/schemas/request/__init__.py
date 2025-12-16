"""
Request DTOs for API endpoints.
"""

# Daily meal requests
from .daily_meal_requests import (
    UserPreferencesRequest,
    MealSuggestionFilterRequest,
    MealTypeEnum
)
# Ingredient-based meal plan requests
from .ingredient_based_meal_plan_requests import (
    IngredientBasedMealPlanRequest
)
# Meal suggestion requests
from .meal_suggestion_requests import (
    MealSuggestionRequest,
    SaveMealSuggestionRequest
)
# Meal plan requests
from .meal_plan_requests import (
    UserPreferencesSchema,
    ConversationMessageRequest,
    ReplaceMealRequest
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
# User requests
from .user_requests import (
    UserSyncRequest,
    UserUpdateLastAccessedRequest,
    UserCreateRequest
)
# Common enums
from ..common.auth_enums import AuthProviderEnum
# Ingredient recognition requests
from .ingredient_recognition_requests import (
    IngredientRecognitionRequest
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
    
    # Meal suggestion
    'MealSuggestionRequest',
    'SaveMealSuggestionRequest',
    
    # Onboarding
    'OnboardingCompleteRequest',
    
    # User
    'UserSyncRequest',
    'UserUpdateLastAccessedRequest',
    'UserCreateRequest',
    
    # Common enums
    'AuthProviderEnum',

    # Ingredient recognition
    'IngredientRecognitionRequest'
]