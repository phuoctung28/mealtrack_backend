import uuid
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict

from src.domain.model.common.enums import MealType  # noqa: F401 — re-exported for backwards compat


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
    seasonings: List[str]
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
        self.seasonings = kwargs.get('seasonings', [])
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
            "seasonings": self.seasonings,
            "instructions": self.instructions,
            "is_vegetarian": self.is_vegetarian,
            "is_vegan": self.is_vegan,
            "is_gluten_free": self.is_gluten_free,
            "cuisine_type": self.cuisine_type
        }


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
    CUT = "cut"
    BULK = "bulk"
    RECOMP = "recomp"
