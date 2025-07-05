"""
Replace meal in plan command.
"""
from dataclasses import dataclass
from typing import Optional, List

from src.app.events.base import Command


@dataclass
class ReplaceMealInPlanCommand(Command):
    """Command to replace a meal in a plan."""
    plan_id: str
    date: str
    meal_id: str
    dietary_preferences: Optional[List[str]] = None
    exclude_ingredients: Optional[List[str]] = None
    preferred_cuisine: Optional[str] = None