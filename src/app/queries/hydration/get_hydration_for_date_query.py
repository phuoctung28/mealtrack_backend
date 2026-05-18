"""Query to fetch hydration entries for a user on a specific date."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class GetHydrationForDateQuery:
    user_id: str
    target_date: date
    header_timezone: Optional[str] = None
