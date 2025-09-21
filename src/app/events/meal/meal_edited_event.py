"""
Event published when a meal is edited.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealEditedEvent(DomainEvent):
    """Event published when a meal is edited."""
    aggregate_id: str
    meal_id: str
    user_id: str
    edit_type: str  # "ingredients_updated", "portions_changed", "ingredient_added", etc.
    changes_summary: str
    nutrition_delta: Dict[str, float]  # Change in nutrition values
    edit_count: int
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
