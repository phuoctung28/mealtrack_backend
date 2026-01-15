"""
Session tracking for meal suggestion system.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.model.meal_planning.meal_suggestion import MealType, MealSize
from src.domain.utils.timezone_utils import utc_now


@dataclass
class SuggestionSession:
    """
    Domain entity tracking a meal suggestion session.

    Sessions expire after 4 hours and track shown suggestions
    to prevent duplicates on regeneration.
    """
    id: str
    user_id: str
    meal_type: MealType
    meal_size: MealSize
    target_calories: int
    ingredients: List[str]
    ingredient_image_url: Optional[str]
    cooking_time_minutes: int
    shown_suggestion_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Set expiration to 4 hours from creation if not provided."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=4)

    def add_shown_ids(self, ids: List[str]) -> None:
        """Track newly shown suggestion IDs to exclude on regenerate."""
        self.shown_suggestion_ids.extend(ids)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return utc_now() > self.expires_at
