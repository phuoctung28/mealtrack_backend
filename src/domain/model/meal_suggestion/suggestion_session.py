"""Suggestion session for tracking user's meal generation flow."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class SuggestionSession:
    """Session tracking for meal suggestion flow (4-hour lifetime)."""
    id: str
    user_id: str
    meal_type: str
    meal_size: str
    target_calories: int
    ingredients: List[str]
    ingredient_image_url: Optional[str]
    cooking_time_minutes: int
    shown_suggestion_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def add_shown_ids(self, ids: List[str]) -> None:
        """Add newly shown suggestion IDs to exclusion list."""
        self.shown_suggestion_ids.extend(ids)

    def __post_init__(self) -> None:
        """Set expiration if not provided."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=4)
