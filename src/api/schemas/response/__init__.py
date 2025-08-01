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
    MessageSchema,
    ConversationMessageResponse,
    StartConversationResponse,
    ConversationHistoryResponse,
    PlannedMealSchema,
    DayPlanSchema,
    MealPlanSummaryResponse,
    ReplaceMealResponse,
    ErrorResponse,
    DailyMealPlanResponse,
    NutritionSummarySchema,
    UserPreferenceSummarySchema
)
# Meal responses
from .meal_responses import (
    SimpleMealResponse,
    DetailedMealResponse,
    MealListResponse,
    MealPhotoAnalysisResponse,
    MealSearchResponse,
    MealStatusResponse,
    NutritionSummaryResponse,
    MacrosResponse,
    NutritionResponse,
    FoodItemResponse,
    MealStatusEnum
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

__all__ = [
    # Daily meal
    'DailyMealSuggestionsResponse',
    'SingleMealSuggestionResponse',
    'SuggestedMealResponse',
    'NutritionTotalsResponse',
    'MealSuggestionErrorResponse',
    'UserMealPlanSummaryResponse',
    
    # Meal
    'SimpleMealResponse',
    'DetailedMealResponse',
    'MealListResponse',
    'MealPhotoAnalysisResponse',
    'MealSearchResponse',
    'MealStatusResponse',
    'NutritionSummaryResponse',
    'MacrosResponse',
    'NutritionResponse',
    'FoodItemResponse',
    'MealStatusEnum',
    
    # TDEE
    'TdeeCalculationResponse',
    'BatchTdeeCalculationResponse',
    'TdeeComparisonResponse',
    'TdeeHistoryResponse',
    'TdeeErrorResponse',
    'MacroTargetsResponse',
    
    # Meal plan
    'MessageSchema',
    'ConversationMessageResponse',
    'StartConversationResponse',
    'ConversationHistoryResponse',
    'PlannedMealSchema',
    'DayPlanSchema',
    'MealPlanSummaryResponse',
    'ReplaceMealResponse',
    'ErrorResponse',
    'DailyMealPlanResponse',
    'NutritionSummarySchema',
    'UserPreferenceSummarySchema',
    
    # Onboarding
    'OnboardingFieldResponse',
    'OnboardingSectionResponse',
    'OnboardingSectionsResponse',
    'OnboardingResponseResponse',
    'OnboardingResponse',
    
    # Daily nutrition
    'DailyNutritionResponse',
    'DailyMacrosResponse',
    
    # Enums
    'MealTypeEnum'
]