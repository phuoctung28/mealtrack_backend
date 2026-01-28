"""
Meal image uploaded event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealImageUploadedEvent(DomainEvent):
    """Event raised when a meal image is uploaded."""
    aggregate_id: str  # This should be the meal_id
    meal_id: str
    image_url: str
    upload_timestamp: datetime
    language: str = "en"  # Target language for translation
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))