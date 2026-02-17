"""
Command to tag a meal as a cheat meal.
"""
from dataclasses import dataclass


@dataclass
class TagCheatMealCommand:
    user_id: str
    meal_id: str
