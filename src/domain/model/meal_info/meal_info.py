"""Meal info domain entity — lightweight meal display data."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MealInfo:
    """
    Lightweight meal display data: name, nutrition description, and image.

    This is intentionally minimal — no recipe steps, no ingredients list,
    no session management. Used for quick meal display cards.
    """

    meal_name: str
    nutrition_description: str
    image_url: Optional[str] = None
    image_source: Optional[str] = None  # "serpapi" | "unsplash" | "gemini" | None
