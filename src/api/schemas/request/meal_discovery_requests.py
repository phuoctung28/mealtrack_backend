"""Request schemas for meal discovery endpoints."""
from typing import List, Optional

from pydantic import BaseModel


class MealDiscoveryRequest(BaseModel):
    """Body for POST /v1/meal-discovery/generate."""

    meal_type: Optional[str] = None         # auto-detected from time if not set
    cuisine_filter: Optional[str] = None    # vietnamese/asian/western/etc
    cooking_time: Optional[str] = None      # quick/medium/long
    calorie_level: Optional[str] = None     # light/regular/hearty
    macro_focus: Optional[str] = None       # high_protein/high_carb/low_fat
    exclude_ids: List[str] = []
    session_id: Optional[str] = None
