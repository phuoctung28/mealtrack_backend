"""Command to attach an uploaded photo to an existing meal."""

from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class AttachMealPhotoCommand(Command):
    """Attach already-uploaded meal image metadata to a meal."""

    meal_id: str
    user_id: str
    image_id: str
    image_url: str
    image_format: str
    size_bytes: int
