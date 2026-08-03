"""
Request DTOs for API endpoints.
"""

# Ingredient recognition requests
# Common enums
from ..common.auth_enums import AuthProviderEnum
from .ingredient_recognition_requests import IngredientRecognitionRequest

# Meal requests
from .meal_requests import (
    AnalyzeMealImageRequest,
    CreateMealRequest,
    MacrosRequest,
    MealSearchRequest,
    UpdateMealMacrosRequest,
    UpdateMealRequest,
)

# Onboarding requests
from .onboarding_requests import OnboardingCompleteRequest

# TDEE requests
from .tdee_requests import (
    BatchTdeeCalculationRequest,
    GoalEnum,
    JobTypeEnum,
    SexEnum,
    TdeeCalculationRequest,
    UnitSystemEnum,
)

# User requests
from .user_requests import (
    UserCreateRequest,
    UserSyncRequest,
    UserUpdateLastAccessedRequest,
)

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
