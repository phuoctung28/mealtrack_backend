"""
Query to get weekly macro budget status.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class GetWeeklyBudgetQuery:
    user_id: str
    target_date: date | None = None  # Defaults to today
    header_timezone: str | None = None  # X-Timezone header fallback
    read_only: bool = False  # Browse callers must not initialize or update state
