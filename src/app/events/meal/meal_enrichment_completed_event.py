"""
Meal enrichment completed event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealEnrichmentCompletedEvent(DomainEvent):
    """Event raised when nutrition enrichment is completed."""
    aggregate_id: str
    meal_id: str
    enriched_items_count: int
    total_nutrition: Dict[str, Any]
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))