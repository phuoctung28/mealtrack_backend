"""
Start meal plan conversation command.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class StartMealPlanConversationCommand(Command):
    """Command to start a meal planning conversation."""
    user_id: str