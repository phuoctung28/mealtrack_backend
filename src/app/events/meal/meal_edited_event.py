"""
Event published when a meal is edited.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

from src.app.events.base import DomainEvent


@dataclass
class MealEditedEvent(DomainEvent):
    """Event published when a meal is edited."""
    meal_id: str
    user_id: str
    edit_type: str  # "ingredients_updated", "portions_changed", "ingredient_added", etc.
    changes_summary: str
    nutrition_delta: Dict[str, float]  # Change in nutrition values
    edit_count: int
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        super().__post_init__()
        self.aggregate_id = self.meal_id
