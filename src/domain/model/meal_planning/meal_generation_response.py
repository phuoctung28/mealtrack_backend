"""
Domain models for meal generation responses.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Any, Optional


@dataclass
class NutritionSummary:
    """Nutritional summary for meals."""
    calories: int
    protein: float
    carbs: float
    fat: float
    
    def __add__(self, other: 'NutritionSummary') -> 'NutritionSummary':
        """Add two nutrition summaries together."""
        return NutritionSummary(
            calories=self.calories + other.calories,
            protein=self.protein + other.protein,
            carbs=self.carbs + other.carbs,
            fat=self.fat + other.fat
        )


@dataclass
class GeneratedMeal:
    """A generated meal with all required information."""
    meal_id: str
    meal_type: str
    name: str
    description: str
    prep_time: int
    cook_time: int
    nutrition: NutritionSummary
    ingredients: List[str]
    seasonings: List[str]
    instructions: List[str]
    is_vegetarian: bool
    is_vegan: bool
    is_gluten_free: bool
    cuisine_type: str
    
    @property
    def total_time(self) -> int:
        """Get total preparation and cooking time."""
        return self.prep_time + self.cook_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "meal_id": self.meal_id,
            "meal_type": self.meal_type,
            "name": self.name,
            "description": self.description,
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "total_time": self.total_time,
            "calories": self.nutrition.calories,
            "protein": self.nutrition.protein,
            "carbs": self.nutrition.carbs,
            "fat": self.nutrition.fat,
            "ingredients": self.ingredients,
            "seasonings": self.seasonings,
            "instructions": self.instructions,
            "is_vegetarian": self.is_vegetarian,
            "is_vegan": self.is_vegan,
            "is_gluten_free": self.is_gluten_free,
            "cuisine_type": self.cuisine_type
        }


@dataclass
class DailyMealPlan:
    """A complete daily meal plan."""
    user_id: str
    plan_date: date
    meals: List[GeneratedMeal]
    
    @property
    def total_nutrition(self) -> NutritionSummary:
        """Calculate total nutrition for all meals."""
        total = NutritionSummary(0, 0.0, 0.0, 0.0)
        for meal in self.meals:
            total = total + meal.nutrition
        return total


@dataclass
class WeeklyMealPlan:
    """A complete weekly meal plan."""
    user_id: str
    start_date: date
    end_date: date
    daily_plans: Dict[str, List[GeneratedMeal]]  # day_name -> meals
    
    @property
    def all_meals(self) -> List[GeneratedMeal]:
        """Get all meals across all days."""
        meals = []
        for day_meals in self.daily_plans.values():
            meals.extend(day_meals)
        return meals
    
    @property
    def total_nutrition(self) -> NutritionSummary:
        """Calculate total nutrition for the week."""
        total = NutritionSummary(0, 0.0, 0.0, 0.0)
        for meal in self.all_meals:
            total = total + meal.nutrition
        return total
    
    @property
    def daily_average_nutrition(self) -> NutritionSummary:
        """Calculate daily average nutrition."""
        total = self.total_nutrition
        return NutritionSummary(
            calories=total.calories // 7,
            protein=round(total.protein / 7, 1),
            carbs=round(total.carbs / 7, 1),
            fat=round(total.fat / 7, 1)
        )


@dataclass
class MealGenerationResult:
    """Result of meal generation operation."""
    success: bool
    daily_plan: Optional[DailyMealPlan] = None
    weekly_plan: Optional[WeeklyMealPlan] = None
    error_message: Optional[str] = None

    def is_daily_plan(self) -> bool:
        """Check if result contains a daily plan."""
        return self.daily_plan is not None

    def is_weekly_plan(self) -> bool:
        """Check if result contains a weekly plan."""
        return self.weekly_plan is not None


@dataclass
class QuickMealIdea:
    """
    A quick meal idea for ingredient-based suggestions.

    Used when user provides ingredients and wants meal ideas.
    Includes simplified info for quick display + pairs_with and quick_recipe.
    """
    meal_id: str
    name: str
    description: str  # Short tagline (10 words max)
    time_minutes: int  # Total cooking time
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    pairs_with: List[str]  # 3-5 complementary ingredients
    quick_recipe: List[str]  # 4-6 simple steps
    tags: List[str]  # ["quick", "high-protein", etc.]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "meal_id": self.meal_id,
            "name": self.name,
            "description": self.description,
            "time_minutes": self.time_minutes,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "pairs_with": self.pairs_with,
            "quick_recipe": self.quick_recipe,
            "tags": self.tags,
        }


@dataclass
class QuickMealSuggestionsResult:
    """Result of quick meal suggestions generation."""
    success: bool
    meals: List[QuickMealIdea]
    error_message: Optional[str] = None