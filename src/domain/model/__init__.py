"""Domain model package."""
# flake8: noqa
from .base import BaseDomainModel
from .meal import (
    Meal,
    MealStatus,
    MealImage,
    Ingredient,
)
from .nutrition import (
    Macros,
    Nutrition,
    FoodItem,
    Food,
)
from .notification import (
    NotificationType,
)
from .chat import (
    Message,
)
from .user import (
    UserDomainModel,
    UserProfileDomainModel,
    UserActivity,
    ActivityLevel,
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
from .meal_planning import (
    SimpleMacroTargets,
    MealPlan,
    PlannedMeal,
    DayPlan,
    MealType,
    UserPreferences,
    DietaryPreference,
    FitnessGoal,
    PlanDuration,
    MealGenerationContext,
    MealGenerationRequest,
    MealGenerationType,
    UserDietaryProfile, # Added
    UserNutritionTargets, # Added
    IngredientConstraints, # Added
    CalorieDistribution, # Added
)