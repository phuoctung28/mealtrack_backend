"""
API Schemas Package

This package contains all Data Transfer Objects (DTOs) and schema definitions
for the MealTrack API, organized by domain and concern separation.

Clean Architecture Structure:
- base.py: Common models, base classes, and shared schemas
- meal_dtos.py: Meal-related request/response DTOs
- ingredient_dtos.py: Ingredient management DTOs
- activity_dtos.py: Activity tracking DTOs
- macros_dtos.py: Nutrition and macros tracking DTOs
- onboarding_dtos.py: User onboarding DTOs

✅ Migration Complete: Legacy files have been successfully removed!
"""

# Application models (imported for backward compatibility)
from app.models import (
    MacrosSchema,
    NutritionSummarySchema,
    PaginationMetadata,
    StatusSchema
)
# Activity DTOs
from .activity_dtos import (
    ActivityEnrichedData,
    ActivityResponse,
    ActivitiesResponse
)
# Base HTTP DTOs
from .base import (
    ImageSchema,
    BaseRequest,
    BaseResponse,
    TimestampedResponse,
    MetadataSchema,
    ErrorResponse,
    ValidationErrorResponse
)
# Ingredient DTOs
from .ingredient_dtos import (
    CreateIngredientRequest,
    UpdateIngredientRequest,
    DeleteIngredientRequest,
    IngredientListRequest,
    IngredientResponse,
    IngredientCreatedResponse,
    IngredientUpdatedResponse,
    IngredientDeletedResponse,
    IngredientListResponse,
    # Food-related DTOs
    FoodResponse,
    CreateFoodRequest,
    FoodSearchRequest,
    PaginatedFoodResponse,
    FoodSearchResponse,
)
# Macros DTOs
from .macros_dtos import (
    OnboardingChoicesRequest,
    ConsumedMacrosRequest,
    MacrosCalculationResponse,
    UpdatedMacrosResponse,
    DailyMacrosResponse
)
# Meal DTOs
from .meal_dtos import (
    CreateMealRequest,
    UpdateMealRequest,
    UpdateMealMacrosRequest,
    MealSearchRequest,
    MealResponse,
    MealStatusResponse,
    DetailedMealResponse,
    IngredientBreakdownSchema,
    MealPhotoResponse,
    PaginatedMealResponse,
    MealSearchResponse
)
# Onboarding DTOs
from .onboarding_dtos import (
    OnboardingFieldResponse,
    OnboardingSectionResponse,
    OnboardingResponseRequest,
    OnboardingSectionsResponse,
    OnboardingResponseResponse
)

# Legacy files have been successfully removed - migration complete! 🎉


__all__ = [
    # HTTP Base DTOs
    "ImageSchema",
    "BaseRequest",
    "BaseResponse",
    "TimestampedResponse", 
    "MetadataSchema",
    "ErrorResponse",
    "ValidationErrorResponse",
    
    # Application models (re-exported)
    "MacrosSchema",
    "NutritionSummarySchema",
    "PaginationMetadata",
    "StatusSchema",
    
    # Meal DTOs
    "CreateMealRequest",
    "UpdateMealRequest", 
    "UpdateMealMacrosRequest",
    "MealSearchRequest",
    "MealResponse",
    "MealStatusResponse",
    "DetailedMealResponse",
    "IngredientBreakdownSchema",
    "MealPhotoResponse",
    "PaginatedMealResponse",
    "MealSearchResponse",
    
    # Ingredient DTOs
    "CreateIngredientRequest",
    "UpdateIngredientRequest",
    "DeleteIngredientRequest",
    "IngredientListRequest",
    "IngredientResponse",
    "IngredientCreatedResponse",
    "IngredientUpdatedResponse", 
    "IngredientDeletedResponse",
    "IngredientListResponse",
    
    # Food DTOs
    "FoodResponse",
    "CreateFoodRequest",
    "FoodSearchRequest",
    "PaginatedFoodResponse",
    "FoodSearchResponse",
    
    # Activity DTOs
    "ActivityEnrichedData",
    "ActivityResponse",
    "ActivityMetadata",
    "ActivitiesResponse",
    
    # Macros DTOs
    "OnboardingChoicesRequest",
    "ConsumedMacrosRequest",
    "MacrosCalculationResponse",
    "UpdatedMacrosResponse",
    "DailyMacrosResponse",
    
    # Onboarding DTOs
    "OnboardingFieldResponse",
    "OnboardingSectionResponse",
    "OnboardingResponseRequest",
    "OnboardingSectionsResponse",
    "OnboardingResponseResponse"
] 