"""Lightweight event requesting cache invalidation for a user's meal date."""
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealCacheInvalidationRequiredEvent(DomainEvent):
    """Published whenever a meal mutation requires cache invalidation."""
    aggregate_id: str = field(default="")
    user_id: str = ""
    meal_date: date = field(default_factory=date.today)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
