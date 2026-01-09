"""Suggestion session for tracking user's meal generation flow."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class SuggestionSession:
    """Session tracking for meal suggestion flow (4-hour lifetime)."""

    id: str
    user_id: str
    meal_type: str  # breakfast, lunch, dinner, snack
    meal_portion_type: str  # snack, main, omad
    target_calories: int
    ingredients: List[str]
    cooking_time_minutes: int
    language: str = "en"  # ISO 639-1 language code (en, vi, es, fr, de, ja, zh)
    shown_suggestion_ids: List[str] = field(default_factory=list)
    shown_meal_names: List[str] = field(default_factory=list)  # Track meal names for exclusion
    dietary_preferences: List[str] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def add_shown_ids(self, ids: List[str]) -> None:
        """Add newly shown suggestion IDs to exclusion list."""
        self.shown_suggestion_ids.extend(ids)
    
    def add_shown_meals(self, meal_names: List[str]) -> None:
        """Add newly shown meal names to exclusion list."""
        self.shown_meal_names.extend(meal_names)

    def __post_init__(self) -> None:
        """Set expiration if not provided."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=4)
