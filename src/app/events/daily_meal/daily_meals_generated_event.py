"""
Daily meals generated event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class DailyMealsGeneratedEvent(DomainEvent):
    """Event raised when daily meals are generated."""
    aggregate_id: str
    user_id: str
    date: str
    meal_count: int
    total_calories: float
    meal_ids: List[str]
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))