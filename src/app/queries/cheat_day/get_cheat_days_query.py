"""Query to get cheat days for a week."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class GetCheatDaysQuery:
    user_id: str
    week_of: Optional[date] = None
