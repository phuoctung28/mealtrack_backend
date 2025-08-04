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
# User requests
from .user_requests import (
    UserSyncRequest,
    UserUpdateLastAccessedRequest,
    UserCreateRequest
)
# Common enums
from ..common.auth_enums import AuthProviderEnum
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
    
    # Onboarding
    'OnboardingCompleteRequest',
    
    # User
    'UserSyncRequest',
    'UserUpdateLastAccessedRequest',
    'UserCreateRequest',
    
    # Common enums
    'AuthProviderEnum'
]