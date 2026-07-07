"""Command to detach a saved photo from an existing meal."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class DeleteMealPhotoCommand(Command):
    """Remove the meal image association for a meal owned by the user."""

    meal_id: str
    user_id: str
