"""
Command to edit meal ingredients and portions.
"""
from dataclasses import dataclass, field
from typing import Optional, List

from src.app.events.base import Command
from src.domain.model.meal.food_item_change import FoodItemChange, CustomNutritionData


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
