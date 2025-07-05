"""
Generate meal plan command.
"""
from dataclasses import dataclass
from typing import Dict, Any

from src.app.events.base import Command


@dataclass
class GenerateMealPlanCommand(Command):
    """Command to generate a meal plan directly."""
    user_id: str
    preferences: Dict[str, Any]