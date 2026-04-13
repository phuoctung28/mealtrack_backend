"""Domain model package."""
# flake8: noqa
from .base import BaseDomainModel
from .meal import (
    Meal,
    MealStatus,
    MealImage,
    Ingredient,
)
from .meal_planning import (
    SimpleMacroTargets,
    PlannedMeal,
    MealType,
    DietaryPreference,
    FitnessGoal,
    MealGenerationContext,
    MealGenerationRequest,
    MealGenerationType,
    UserDietaryProfile,  # Added
    UserNutritionTargets,  # Added
    IngredientConstraints,  # Added
    CalorieDistribution,  # Added
)
from .notification import (
    NotificationType,
)
from .nutrition import (
    Macros,
    Nutrition,
    FoodItem,
    Food,
)
from .user import (
    UserDomainModel,
    UserProfileDomainModel,
    UserActivity,
    JobType,
    OnboardingSection,
    OnboardingResponse,
    TDEE,
    TdeeRequest,
    TdeeResponse,
    Sex,
    Goal,
    UnitSystem,
    UserMacros,
    MacroTargets,
)
