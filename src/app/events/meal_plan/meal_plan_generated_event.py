"""
Meal plan generated event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealPlanGeneratedEvent(DomainEvent):
    """Event raised when meal plan is generated."""
    aggregate_id: str
    plan_id: str
    user_id: str
    days: int
    total_meals: int
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))