"""Command to sync weight entries from mobile."""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class WeightEntryData:
    """Single weight entry for sync."""

    weight_kg: float
    recorded_at: datetime


@dataclass
class SyncWeightEntriesCommand:
    """Bulk sync weight entries from mobile."""

    user_id: str
    entries: List[WeightEntryData]
