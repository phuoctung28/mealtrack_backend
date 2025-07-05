"""
Meal analysis started event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealAnalysisStartedEvent(DomainEvent):
    """Event raised when meal analysis starts."""
    aggregate_id: str
    meal_id: str
    analysis_type: str = "vision_ai"
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))