"""
Query to get weekly macro budget status.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class GetWeeklyBudgetQuery:
    user_id: str
    target_date: Optional[date] = None  # Defaults to today
    header_timezone: Optional[str] = None  # X-Timezone header fallback
