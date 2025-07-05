"""
Meal enrichment started event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealEnrichmentStartedEvent(DomainEvent):
    """Event raised when nutrition enrichment starts."""
    aggregate_id: str
    meal_id: str
    food_items_count: int
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))