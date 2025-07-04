import uuid
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict


class DietaryPreference(str, Enum):
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    PESCATARIAN = "pescatarian"
    GLUTEN_FREE = "gluten_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    DAIRY_FREE = "dairy_free"
    NONE = "none"


class FitnessGoal(str, Enum):
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    GENERAL_HEALTH = "general_health"


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class PlanDuration(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class UserPreferences:
    """User preferences for meal planning"""
    dietary_preferences: List[DietaryPreference]
    allergies: List[str]
    fitness_goal: FitnessGoal
    meals_per_day: int
    snacks_per_day: int
    cooking_time_weekday: int  # minutes
    cooking_time_weekend: int  # minutes
    favorite_cuisines: List[str]
    disliked_ingredients: List[str]
    plan_duration: PlanDuration = PlanDuration.WEEKLY
    
    def to_dict(self) -> Dict:
        return {
            "dietary_preferences": [pref.value for pref in self.dietary_preferences],
            "allergies": self.allergies,
            "fitness_goal": self.fitness_goal.value,
            "meals_per_day": self.meals_per_day,
            "snacks_per_day": self.snacks_per_day,
            "cooking_time_weekday": self.cooking_time_weekday,
            "cooking_time_weekend": self.cooking_time_weekend,
            "favorite_cuisines": self.favorite_cuisines,
            "disliked_ingredients": self.disliked_ingredients,
            "plan_duration": self.plan_duration.value
        }


@dataclass
class PlannedMeal:
    """Represents a single meal in a meal plan"""
    meal_id: str
    meal_type: MealType
    name: str
    description: str
    prep_time: int  # minutes
    cook_time: int  # minutes
    calories: int
    protein: float  # grams
    carbs: float  # grams
    fat: float  # grams
    ingredients: List[str]
    instructions: List[str]
    is_vegetarian: bool
    is_vegan: bool
    is_gluten_free: bool
    cuisine_type: Optional[str] = None
    
    def __init__(self, **kwargs):
        self.meal_id = kwargs.get('meal_id', str(uuid.uuid4()))
        self.meal_type = kwargs['meal_type']
        self.name = kwargs['name']
        self.description = kwargs['description']
        self.prep_time = kwargs['prep_time']
        self.cook_time = kwargs['cook_time']
        self.calories = kwargs['calories']
        self.protein = kwargs['protein']
        self.carbs = kwargs['carbs']
        self.fat = kwargs['fat']
        self.ingredients = kwargs['ingredients']
        self.instructions = kwargs['instructions']
        self.is_vegetarian = kwargs['is_vegetarian']
        self.is_vegan = kwargs['is_vegan']
        self.is_gluten_free = kwargs['is_gluten_free']
        self.cuisine_type = kwargs.get('cuisine_type')
    
    @property
    def total_time(self) -> int:
        return self.prep_time + self.cook_time
    
    def to_dict(self) -> Dict:
        return {
            "meal_id": self.meal_id,
            "meal_type": self.meal_type.value,
            "name": self.name,
            "description": self.description,
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "total_time": self.total_time,
            "calories": self.calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat,
            "ingredients": self.ingredients,
            "instructions": self.instructions,
            "is_vegetarian": self.is_vegetarian,
            "is_vegan": self.is_vegan,
            "is_gluten_free": self.is_gluten_free,
            "cuisine_type": self.cuisine_type
        }


@dataclass
class DayPlan:
    """Represents meals for a single day"""
    date: date
    meals: List[PlannedMeal]
    
    def get_meals_by_type(self, meal_type: MealType) -> List[PlannedMeal]:
        return [meal for meal in self.meals if meal.meal_type == meal_type]
    
    def get_total_nutrition(self) -> Dict[str, float]:
        return {
            "calories": sum(meal.calories for meal in self.meals),
            "protein": sum(meal.protein for meal in self.meals),
            "carbs": sum(meal.carbs for meal in self.meals),
            "fat": sum(meal.fat for meal in self.meals)
        }
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "meals": [meal.to_dict() for meal in self.meals],
            "total_nutrition": self.get_total_nutrition()
        }


@dataclass
class MealPlan:
    """Represents a complete meal plan (daily or weekly)"""
    plan_id: str
    user_id: str
    preferences: UserPreferences
    days: List[DayPlan]
    created_at: datetime
    updated_at: datetime
    
    def __init__(self, user_id: str, preferences: UserPreferences, days: List[DayPlan]):
        self.plan_id = str(uuid.uuid4())
        self.user_id = user_id
        self.preferences = preferences
        self.days = days
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def get_day(self, date: date) -> Optional[DayPlan]:
        for day in self.days:
            if day.date == date:
                return day
        return None
    
    def replace_meal(self, date: date, meal_id: str, new_meal: PlannedMeal) -> bool:
        day = self.get_day(date)
        if day:
            for i, meal in enumerate(day.meals):
                if meal.meal_id == meal_id:
                    day.meals[i] = new_meal
                    self.updated_at = datetime.utcnow()
                    return True
        return False
    
    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "preferences": self.preferences.to_dict(),
            "days": [day.to_dict() for day in self.days],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }