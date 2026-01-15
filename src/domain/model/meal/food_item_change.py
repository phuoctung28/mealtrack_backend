"""
Domain model for food item changes.
Used when editing meals to add, update, or remove food items.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FoodItemChange:
    """Represents a change to a food item in meal editing."""
    action: str  # "add", "update", "remove"
    id: Optional[str] = None
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
