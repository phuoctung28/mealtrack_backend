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
    MealSuggestionErrorResponse,
    UserMealPlanSummaryResponse,
    MealTypeEnum,
    QuickMealIdeaResponse,
    QuickMealSuggestionsResponse
)
# Daily nutrition responses
from .daily_nutrition_response import (
    DailyNutritionResponse,
    MacrosResponse as DailyMacrosResponse
)
# Ingredient recognition responses
from .ingredient_recognition_responses import (
    IngredientRecognitionResponse,
    IngredientCategoryEnum
)
# Ingredient responses
# Macros responses
# Meal responses
from .meal_responses import (
    SimpleMealResponse,
    DetailedMealResponse,
    MealListResponse,
    MealPhotoAnalysisResponse,
    AsyncMealImageAnalysisAcceptedResponse,
    MealSearchResponse,
    NutritionSummaryResponse,
    MacrosResponse,
    NutritionResponse,
    FoodItemResponse,
    ManualMealCreationResponse,
    MealStatusEnum
)
# Meal suggestion responses
from .meal_suggestion_responses import (
    MealSuggestionItem,
    MealSuggestionsResponse,
    MacrosSchema as MealSuggestionMacrosSchema
)
# Onboarding responses
from .onboarding_responses import (
    OnboardingFieldResponse,
    OnboardingSectionResponse,
    OnboardingSectionsResponse,
    OnboardingResponseResponse,
    OnboardingResponse
)
# TDEE responses
from .tdee_responses import (
    TdeeCalculationResponse,
    BatchTdeeCalculationResponse,
    TdeeComparisonResponse,
    TdeeHistoryResponse,
    TdeeErrorResponse,
    MacroTargetsResponse
)
# User responses
from .user_responses import (
    UserProfileResponse,
    UserSyncResponse,
    UserStatusResponse,
    UserUpdateResponse,
    UserMetricsResponse
)

__all__ = [
    # Daily meal
    'DailyMealSuggestionsResponse',
    'SingleMealSuggestionResponse',
    'SuggestedMealResponse',
    'NutritionTotalsResponse',
    'MealSuggestionErrorResponse',
    'UserMealPlanSummaryResponse',
    'QuickMealIdeaResponse',
    'QuickMealSuggestionsResponse',
    
    # Meal
    'SimpleMealResponse',
    'DetailedMealResponse',
    'MealListResponse',
    'MealPhotoAnalysisResponse',
    'AsyncMealImageAnalysisAcceptedResponse',
    'MealSearchResponse',
    'NutritionSummaryResponse',
    'MacrosResponse',
    'NutritionResponse',
    'FoodItemResponse',
    'ManualMealCreationResponse',
    'MealStatusEnum',
    
    # TDEE
    'TdeeCalculationResponse',
    'BatchTdeeCalculationResponse',
    'TdeeComparisonResponse',
    'TdeeHistoryResponse',
    'TdeeErrorResponse',
    'MacroTargetsResponse',
    
    # Meal suggestion
    'MealSuggestionItem',
    'MealSuggestionsResponse',
    'MealSuggestionMacrosSchema',

    # Onboarding
    'OnboardingFieldResponse',
    'OnboardingSectionResponse',
    'OnboardingSectionsResponse',
    'OnboardingResponseResponse',
    'OnboardingResponse',
    
    # Daily nutrition
    'DailyNutritionResponse',
    'DailyMacrosResponse',
    
    # User
    'UserProfileResponse',
    'UserSyncResponse',
    'UserStatusResponse',
    'UserUpdateResponse',
    'UserMetricsResponse',

    # Enums
    'MealTypeEnum',

    # Ingredient recognition
    'IngredientRecognitionResponse',
    'IngredientCategoryEnum'
]