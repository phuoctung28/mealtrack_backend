"""
Save user onboarding command.
"""
from dataclasses import dataclass
from typing import Optional, List

from src.app.events.base import Command


@dataclass
class SaveUserOnboardingCommand(Command):
    """Command to save user onboarding data."""
    user_id: str
    # Personal info
    age: int
    gender: str
    height_cm: float
    weight_kg: float

    # Goals
    activity_level: str
    fitness_goal: str

    # Preferences - REQUIRED
    pain_points: List[str]
    dietary_preferences: List[str]

    # Meal preferences
    meals_per_day: int = 3

    # Optional fields
    body_fat_percentage: Optional[float] = None
