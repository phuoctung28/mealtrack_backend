"""
Meal nutrition updated event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealNutritionUpdatedEvent(DomainEvent):
    """Event raised when meal nutrition is updated."""
    aggregate_id: str
    meal_id: str
    old_weight: float
    new_weight: float
    updated_nutrition: Dict[str, Any]
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))