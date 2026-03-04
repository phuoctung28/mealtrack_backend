"""
Command to create a manual meal from a list of USDA FDC items or custom foods with portions.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from src.app.events.base import Command


@dataclass
class CustomNutrition:
    """Custom nutrition data for non-USDA foods."""
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float


@dataclass
class ManualMealItem:
    """Manual meal item - either USDA (fdc_id) or custom (name + nutrition)."""
    fdc_id: Optional[int] = None
    name: Optional[str] = None
    quantity: float = 1.0  # in grams or unit-specified grams base
    unit: str = "g"      # unit name, e.g., "g"
    custom_nutrition: Optional[CustomNutrition] = None


@dataclass
class CreateManualMealCommand(Command):
    user_id: str
    items: List[ManualMealItem]
    dish_name: str
    meal_type: Optional[str] = None
    target_date: Optional[date] = None
    source: Optional[str] = None  # scanner, prompt, food_search, manual
