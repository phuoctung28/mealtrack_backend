"""
Meal analysis completed event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class MealAnalysisCompletedEvent(DomainEvent):
    """Event raised when meal analysis is completed."""
    aggregate_id: str
    meal_id: str
    dish_name: str
    nutrition_data: Dict[str, Any]
    food_items: List[Dict[str, Any]]
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))