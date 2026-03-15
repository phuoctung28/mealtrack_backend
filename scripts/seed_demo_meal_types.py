"""Shared dataclasses for demo meal seed data."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class FoodItemData:
    """Macro data for a single food ingredient."""
    name: str
    quantity: float
    unit: str
    protein: float
    carbs: float
    fat: float
    fiber: float = 0.0
    sugar: float = 0.0


@dataclass
class MealData:
    """A single meal with food items and aggregation helpers."""
    dish_name: str
    meal_type: str  # breakfast, lunch, dinner, snack
    food_items: List[FoodItemData] = field(default_factory=list)
    source: str = "manual"

    def total_protein(self) -> float:
        return round(sum(i.protein for i in self.food_items), 1)

    def total_carbs(self) -> float:
        return round(sum(i.carbs for i in self.food_items), 1)

    def total_fat(self) -> float:
        return round(sum(i.fat for i in self.food_items), 1)

    def total_fiber(self) -> float:
        return round(sum(i.fiber for i in self.food_items), 1)

    def total_sugar(self) -> float:
        return round(sum(i.sugar for i in self.food_items), 1)
