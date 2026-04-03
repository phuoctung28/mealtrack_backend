"""Request schemas for meal discovery endpoints."""
from typing import List, Optional

from pydantic import BaseModel


class MealDiscoveryRequest(BaseModel):
    """Body for POST /v1/meal-discovery/generate."""

    meal_type: Optional[str] = None       # breakfast/lunch/dinner/snack
    cuisine_filter: Optional[str] = None  # vietnamese/asian/western
    exclude_ids: List[str] = []
    session_id: Optional[str] = None      # Resume existing session to avoid duplicates
