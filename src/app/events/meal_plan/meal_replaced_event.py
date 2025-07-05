"""
Meal replaced event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealReplacedEvent(DomainEvent):
    """Event raised when a meal is replaced in plan."""
    aggregate_id: str
    plan_id: str
    old_meal_id: str
    new_meal_id: str
    date: str
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))