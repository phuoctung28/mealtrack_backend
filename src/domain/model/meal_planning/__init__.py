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
    PlannedMeal,
    DietaryPreference,
    FitnessGoal,
    MealType,
)
from .meal_suggestion import (
    MealSuggestion,
    MealSize,
    SuggestionStatus,
    Ingredient,
    RecipeStep,
    MacroEstimate,
    MEAL_SIZE_PERCENTAGES
)

__all__ = [
    'PlannedMeal',
    'DietaryPreference',
    'FitnessGoal',
    'MealType',
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
    'MealSuggestion',
    'MealSize',
    'SuggestionStatus',
    'Ingredient',
    'RecipeStep',
    'MacroEstimate',
    'MEAL_SIZE_PERCENTAGES',
]

