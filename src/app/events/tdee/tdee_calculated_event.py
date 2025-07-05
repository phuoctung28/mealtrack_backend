"""
TDEE calculated event.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from src.app.events.base import DomainEvent


@dataclass
class TdeeCalculatedEvent(DomainEvent):
    """Event raised when TDEE is calculated."""
    aggregate_id: str
    user_id: str
    bmr: float
    tdee: float
    target_calories: float
    formula_used: str
    calculation_params: Dict[str, Any]
    # Metadata fields with defaults
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))