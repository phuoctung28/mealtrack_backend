"""
Command for recognizing an ingredient from an image.
"""
from dataclasses import dataclass

from src.app.events.base import Command


@dataclass
class RecognizeIngredientCommand(Command):
    """
    Command to recognize an ingredient from an image.

    Uses Gemini Vision AI to identify the primary food ingredient
    in the provided image data.
    """

    image_data: str  # Base64 encoded image
