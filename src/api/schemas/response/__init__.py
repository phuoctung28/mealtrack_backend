"""
Response DTOs for API endpoints.
"""

# Activity responses
# Daily meal responses
from .daily_meal_responses import (
    DailyMealSuggestionsResponse,
    SingleMealSuggestionResponse,
    SuggestedMealResponse,
    NutritionTotalsResponse,
    MealTypeEnum
)
# Daily nutrition responses
from .daily_nutrition_response import (
    DailyNutritionResponse,
    MacrosResponse as DailyMacrosResponse
)
# Ingredient responses
# Macros responses
# Meal plan responses
from .meal_plan_responses import (
    ReplaceMealResponse,
    DailyMealPlanStrongResponse,
    GeneratedMealResponse,
    UserPreferencesStrongResponse,
    NutritionSummarySchema,
    MealsByDateResponse,
    MealPlanGenerationStatusResponse
)
# Meal responses
from .meal_responses import (
    SimpleMealResponse,
    DetailedMealResponse,
    MealListResponse,
    MealStatusResponse,
    MacrosResponse,
    NutritionResponse,
    FoodItemResponse,
    MealStatusEnum
)
# Onboarding responses
from .onboarding_responses import (
    OnboardingResponse
)
# TDEE responses
from .tdee_responses import (
    TdeeCalculationResponse,
    MacroTargetsResponse
)
# User responses
from .user_responses import (
    UserProfileResponse,
    UserSyncResponse,
    UserStatusResponse,
    UserUpdateResponse
)
# Weekly meal plan responses

__all__ = [
    # Daily meal
    'DailyMealSuggestionsResponse',
    'SingleMealSuggestionResponse',
    'SuggestedMealResponse',
    'NutritionTotalsResponse',

    # Meal
    'SimpleMealResponse',
    'DetailedMealResponse',
    'MealListResponse',
    'MealStatusResponse',
    'MacrosResponse',
    'NutritionResponse',
    'FoodItemResponse',
    'MealStatusEnum',

    # TDEE
    'TdeeCalculationResponse',
    'MacroTargetsResponse',

    # Meal plan
    'ReplaceMealResponse',
    'DailyMealPlanStrongResponse',
    'GeneratedMealResponse',
    'UserPreferencesStrongResponse',
    'NutritionSummarySchema',
    'MealsByDateResponse',
    'MealPlanGenerationStatusResponse',

    # Onboarding
    'OnboardingResponse',

    # Daily nutrition
    'DailyNutritionResponse',
    'DailyMacrosResponse',

    # User
    'UserProfileResponse',
    'UserSyncResponse',
    'UserStatusResponse',
    'UserUpdateResponse',

    # Enums
    'MealTypeEnum'
]