"""
Bulk nutrition query for fetching multiple dates at once.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class GetNutritionBulkQuery(Query):
    """Query to get nutrition summaries for a date range."""
    user_id: str
    start_date: date
    end_date: date
    header_timezone: Optional[str] = None
