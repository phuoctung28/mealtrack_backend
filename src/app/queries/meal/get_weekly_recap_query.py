"""
Query to get weekly performance recap.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class GetWeeklyRecapQuery:
    user_id: str
    week_start: Optional[date] = None  # If None, defaults to previous week's Monday
    header_timezone: Optional[str] = None  # X-Timezone header fallback
