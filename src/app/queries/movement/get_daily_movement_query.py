"""Query for daily movement summary."""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetDailyMovementQuery(Query):
    user_id: str
    target_date: Optional[date] = None
    header_timezone: Optional[str] = None
