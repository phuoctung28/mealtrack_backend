"""
User onboarded event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class UserOnboardedEvent(DomainEvent):
    """Event raised when user completes onboarding."""
    aggregate_id: str
    user_id: str
    profile_id: str
    tdee: float
    target_calories: float
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))