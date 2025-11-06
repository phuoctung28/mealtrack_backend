"""
Domain models for meal generation requests.
"""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Dict, Optional

from .meal_plan import MealType


class MealGenerationType(Enum):
    """Types of meal generation requests."""
    DAILY_PROFILE_BASED = "daily_profile_based"
    DAILY_INGREDIENT_BASED = "daily_ingredient_based"
    WEEKLY_INGREDIENT_BASED = "weekly_ingredient_based"


@dataclass
class UserNutritionTargets:
    """User's nutritional targets."""
    calories: int
    protein: float
    carbs: float
    fat: float


@dataclass
class UserDietaryProfile:
    """User's dietary profile and preferences."""
    user_id: str
    dietary_preferences: List[str]
    allergies: List[str]
    health_conditions: List[str]
    activity_level: str
    fitness_goal: str
    meals_per_day: int
    include_snacks: bool
    age: Optional[int] = None
    gender: Optional[str] = None


@dataclass
class IngredientConstraints:
    """Available ingredients and seasonings for meal generation."""
    available_ingredients: List[str]
    available_seasonings: List[str]


@dataclass
class MealGenerationRequest:
    """Base request for meal generation."""
    generation_type: MealGenerationType
    user_profile: UserDietaryProfile
    nutrition_targets: UserNutritionTargets
    ingredient_constraints: Optional[IngredientConstraints] = None


@dataclass
class CalorieDistribution:
    """Calorie distribution across meal types."""
    distribution: Dict[MealType, int]
    
    def get_calories_for_meal(self, meal_type: MealType) -> int:
        """Get calorie target for specific meal type."""
        return self.distribution.get(meal_type, 0)
    
    def total_calories(self) -> int:
        """Get total calories across all meals."""
        return sum(self.distribution.values())


@dataclass
class MealGenerationContext:
    """Context for generating a specific meal plan."""
    request: MealGenerationRequest
    calorie_distribution: CalorieDistribution
    meal_types: List[MealType]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    def is_ingredient_based(self) -> bool:
        """Check if this is an ingredient-based generation."""
        return self.request.ingredient_constraints is not None
    
    def is_weekly_plan(self) -> bool:
        """Check if this is a weekly plan generation."""
        return self.request.generation_type == MealGenerationType.WEEKLY_INGREDIENT_BASED