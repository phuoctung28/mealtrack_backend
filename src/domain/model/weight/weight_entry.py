"""Weight entry domain entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class WeightEntry:
    """A single weight log entry for a user."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    weight_kg: float = 0.0
    recorded_at: datetime = field(default_factory=datetime.utcnow)
    created_at: Optional[datetime] = None
