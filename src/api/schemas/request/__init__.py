"""
Request DTOs for API endpoints.
"""

# Ingredient recognition requests
from .ingredient_recognition_requests import IngredientRecognitionRequest

# Meal requests
from .meal_requests import (
    CreateMealRequest,
    UpdateMealRequest,
    UpdateMealMacrosRequest,
    MealSearchRequest,
    AnalyzeMealImageRequest,
    MacrosRequest,
)

# Meal suggestion requests
from .meal_suggestion_requests import MealSuggestionRequest

# Onboarding requests
from .onboarding_requests import OnboardingCompleteRequest

# TDEE requests
from .tdee_requests import (
    TdeeCalculationRequest,
    BatchTdeeCalculationRequest,
    SexEnum,
    JobTypeEnum,
    GoalEnum,
    UnitSystemEnum,
)

# User requests
from .user_requests import (
    UserSyncRequest,
    UserUpdateLastAccessedRequest,
    UserCreateRequest,
)

# Common enums
from ..common.auth_enums import AuthProviderEnum

__all__ = [
    # Meal
    "CreateMealRequest",
    "UpdateMealRequest",
    "UpdateMealMacrosRequest",
    "MealSearchRequest",
    "AnalyzeMealImageRequest",
    "MacrosRequest",
    # TDEE
    "TdeeCalculationRequest",
    "BatchTdeeCalculationRequest",
    "SexEnum",
    "JobTypeEnum",
    "GoalEnum",
    "UnitSystemEnum",
    # Meal suggestion
    "MealSuggestionRequest",
    # Onboarding
    "OnboardingCompleteRequest",
    # User
    "UserSyncRequest",
    "UserUpdateLastAccessedRequest",
    "UserCreateRequest",
    # Common enums
    "AuthProviderEnum",
    # Ingredient recognition
    "IngredientRecognitionRequest",
]
