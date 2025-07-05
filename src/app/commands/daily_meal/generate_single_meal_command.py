"""
Generate single meal command.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict

from src.app.events.base import Command


@dataclass
class GenerateSingleMealCommand(Command):
    """Command to generate a single meal suggestion."""
    meal_type: str
    age: int
    gender: str
    height: float
    weight: float
    activity_level: str
    goal: str
    dietary_preferences: Optional[List[str]] = None
    health_conditions: Optional[List[str]] = None
    target_calories: Optional[float] = None
    target_macros: Optional[Dict[str, float]] = None