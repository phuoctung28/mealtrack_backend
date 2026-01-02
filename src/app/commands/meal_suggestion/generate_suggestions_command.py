"""Generate meal suggestions command (Phase 06)."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GenerateSuggestionsCommandV2:
    """Command to generate 3 meal suggestions with session tracking."""

    user_id: str
    meal_type: str
    meal_portion_type: str  # snack, main, omad
    ingredients: List[str]
    ingredient_image_url: Optional[str]
    cooking_time_minutes: int
