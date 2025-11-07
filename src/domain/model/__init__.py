"""
Domain models organized by bounded context.

This module re-exports all domain models from their bounded contexts for convenience.
"""
# AI context
from .ai import (
    GPTMacros,
    GPTFoodItem,
    GPTAnalysisResponse,
    GPTResponseError,
    GPTResponseFormatError,
    GPTResponseValidationError,
    GPTResponseParsingError,
    GPTResponseIncompleteError,
)
# Conversation context
from .conversation import (
    Conversation,
    Message,
    MessageRole,
    ConversationContext,
    ConversationState,
    PromptContext,
    MealsForDateResponse,
)
# Meal context
from .meal import Meal, MealStatus, MealImage, Ingredient
# Meal Planning context
from .meal_planning import (
    MealPlan,
    PlannedMeal,
    DayPlan,
    UserPreferences,
    DietaryPreference,
    FitnessGoal,
    MealType,
    PlanDuration,
    SimpleMacroTargets,
    MealGenerationRequest,
    MealGenerationType,
    MealGenerationContext,
    UserDietaryProfile,
    UserNutritionTargets,
    IngredientConstraints,
    CalorieDistribution,
    DailyMealPlan,
    GeneratedMeal,
    NutritionSummary,
)
# Notification context
from .notification import (
    UserFcmToken,
    NotificationPreferences,
    PushNotification,
    DeviceType,
    NotificationType,
)
# Nutrition context
from .nutrition import Nutrition, FoodItem, Macros, Micros, Food
# User context
from .user import (
    Activity,
    ActivityType,
    UserMacros,
    OnboardingSection,
    OnboardingField,
    OnboardingResponse,
    OnboardingSectionType,
    FieldType,
    TdeeRequest,
    TdeeResponse,
    MacroTargets,
    Sex,
    ActivityLevel,
    Goal,
    UnitSystem,
)

__all__ = [
    # Meal
    'Meal',
    'MealStatus',
    'MealImage',
    'Ingredient',
    # Nutrition
    'Nutrition',
    'FoodItem',
    'Macros',
    'Micros',
    'Food',
    # User
    'Activity',
    'ActivityType',
    'UserMacros',
    'OnboardingSection',
    'OnboardingField',
    'OnboardingResponse',
    'OnboardingSectionType',
    'FieldType',
    'TdeeRequest',
    'TdeeResponse',
    'MacroTargets',
    'Sex',
    'ActivityLevel',
    'Goal',
    'UnitSystem',
    # Meal Planning
    'MealPlan',
    'PlannedMeal',
    'DayPlan',
    'UserPreferences',
    'DietaryPreference',
    'FitnessGoal',
    'MealType',
    'PlanDuration',
    'SimpleMacroTargets',
    'MealGenerationRequest',
    'MealGenerationType',
    'MealGenerationContext',
    'UserDietaryProfile',
    'UserNutritionTargets',
    'IngredientConstraints',
    'CalorieDistribution',
    'DailyMealPlan',
    'GeneratedMeal',
    'NutritionSummary',
    # Conversation
    'Conversation',
    'Message',
    'MessageRole',
    'ConversationContext',
    'ConversationState',
    'PromptContext',
    'MealsForDateResponse',
    # AI
    'GPTMacros',
    'GPTFoodItem',
    'GPTAnalysisResponse',
    'GPTResponseError',
    'GPTResponseFormatError',
    'GPTResponseValidationError',
    'GPTResponseParsingError',
    'GPTResponseIncompleteError',
    # Notification
    'UserFcmToken',
    'NotificationPreferences',
    'PushNotification',
    'DeviceType',
    'NotificationType',
]
