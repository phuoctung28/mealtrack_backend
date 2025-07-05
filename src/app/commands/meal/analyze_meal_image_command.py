"""
Analyze meal image command.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class AnalyzeMealImageCommand(Command):
    """Command to analyze a meal image."""
    meal_id: str