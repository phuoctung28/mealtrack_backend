"""Response schemas for the meal info generation endpoint."""
from typing import Optional

from pydantic import BaseModel


class MealInfoResponse(BaseModel):
    """Response for POST /v1/meal-info/generate."""

    meal_name: str
    nutrition_description: str
    image_url: Optional[str] = None
    image_source: Optional[str] = None  # "serpapi" | "unsplash" | "gemini" | null
