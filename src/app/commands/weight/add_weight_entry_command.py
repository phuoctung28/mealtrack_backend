"""Command to add a weight entry."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AddWeightEntryCommand:
    """Add a single weight entry."""

    user_id: str
    weight_kg: float
    recorded_at: datetime
