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
    
    # Optional fields at the end
    body_fat_percentage: Optional[float] = None
    target_weight_kg: Optional[float] = None
    meals_per_day: int = 3
    snacks_per_day: int = 1
    
    # Preferences
    dietary_preferences: Optional[List[str]] = None
    health_conditions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None