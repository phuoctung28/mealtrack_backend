"""
Meal Planning bounded context - Domain models for meal planning and generation.
"""
from .macro_targets import SimpleMacroTargets
from .meal_generation_request import (
    MealGenerationRequest,
    MealGenerationType,
    MealGenerationContext,
    UserDietaryProfile,
    UserNutritionTargets,
    IngredientConstraints,
    CalorieDistribution
)
from .meal_generation_response import (
    DailyMealPlan,
    GeneratedMeal,
    NutritionSummary
)
from .meal_plan import (
    MealPlan,
    PlannedMeal,
    DayPlan,
    UserPreferences,
    DietaryPreference,
    FitnessGoal,
    MealType,
    PlanDuration
)

__all__ = [
    'MealPlan',
    'PlannedMeal',
    'DayPlan',
    'UserPreferences',
    'DietaryPreference',
    'FitnessGoal',
    'MealType',
    'PlanDuration',
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
    'SimpleMacroTargets',
]

