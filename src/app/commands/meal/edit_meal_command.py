"""
Command to edit meal ingredients and portions.
"""
from dataclasses import dataclass, field
from typing import Optional, List

from src.app.events.base import Command


@dataclass
class FoodItemChange:
    """Represents a change to a food item in meal editing."""
    action: str  # "add", "update", "remove"
    food_item_id: Optional[str] = None
    fdc_id: Optional[int] = None
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    custom_nutrition: Optional['CustomNutritionData'] = None


@dataclass
class CustomNutritionData:
    """Custom nutrition data for non-USDA ingredients."""
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    fiber_per_100g: Optional[float] = None


@dataclass
class EditMealCommand(Command):
    """Command to edit a meal's ingredients."""
    meal_id: str
    dish_name: Optional[str] = None
    food_item_changes: List[FoodItemChange] = field(default_factory=list)


@dataclass
class AddCustomIngredientCommand(Command):
    """Command to add a custom ingredient to a meal."""
    meal_id: str
    name: str
    quantity: float
    unit: str
    nutrition: CustomNutritionData
