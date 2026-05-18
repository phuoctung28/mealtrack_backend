"""Command to log a hydration entry."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.model.hydration.hydration_entry import DrinkType


@dataclass
class LogHydrationCommand:
    user_id: str
    drink_type: DrinkType
    volume_ml: int
    logged_at: datetime
