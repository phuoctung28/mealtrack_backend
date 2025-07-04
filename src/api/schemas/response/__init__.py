"""
Response DTOs for API endpoints.
"""

# Activity responses
from .activity_responses import (
    ActivityResponse,
    ActivitiesListResponse
)
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
# Ingredient responses
from .ingredient_responses import (
    IngredientResponse,
    IngredientListResponse,
    IngredientCreatedResponse,
    IngredientUpdatedResponse,
    IngredientDeletedResponse
)
# Macros responses
from .macros_responses import (
    MacrosCalculationResponse,
    UpdatedMacrosResponse,
    DailyMacrosResponse
)
# Meal plan responses
from .meal_plan_responses import (
    MessageSchema,
    ConversationMessageResponse,
    StartConversationResponse,
    ConversationHistoryResponse,
    PlannedMealSchema,
    DayPlanSchema,
    MealPlanResponse,
    MealPlanSummaryResponse,
    ReplaceMealResponse,
    ErrorResponse
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
    OnboardingResponseResponse
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
    
    # Activity
    'ActivityResponse',
    'ActivitiesListResponse',
    
    # Macros
    'MacrosCalculationResponse',
    'UpdatedMacrosResponse',
    'DailyMacrosResponse',
    
    # Ingredient
    'IngredientResponse',
    'IngredientListResponse',
    'IngredientCreatedResponse',
    'IngredientUpdatedResponse',
    'IngredientDeletedResponse',
    
    # Meal plan
    'MessageSchema',
    'ConversationMessageResponse',
    'StartConversationResponse',
    'ConversationHistoryResponse',
    'PlannedMealSchema',
    'DayPlanSchema',
    'MealPlanResponse',
    'MealPlanSummaryResponse',
    'ReplaceMealResponse',
    'ErrorResponse',
    
    # Onboarding
    'OnboardingFieldResponse',
    'OnboardingSectionResponse',
    'OnboardingSectionsResponse',
    'OnboardingResponseResponse',
    
    # Enums
    'MealTypeEnum'
]