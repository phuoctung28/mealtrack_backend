"""
Domain models for meal generation responses.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Any


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
