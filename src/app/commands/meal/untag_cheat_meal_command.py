"""
Command to untag a cheat meal.
"""
from dataclasses import dataclass


@dataclass
class UntagCheatMealCommand:
    user_id: str
    meal_id: str
