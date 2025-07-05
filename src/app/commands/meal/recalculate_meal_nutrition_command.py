"""
Recalculate meal nutrition command.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class RecalculateMealNutritionCommand(Command):
    """Command to recalculate meal nutrition with new weight."""
    meal_id: str
    weight_grams: float