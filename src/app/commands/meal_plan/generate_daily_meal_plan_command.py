"""
Generate daily meal plan command.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class GenerateDailyMealPlanCommand(Command):
    """Command to generate a daily meal plan based on user profile."""
    user_id: str 