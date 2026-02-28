"""
Query to preview TDEE calculation without authentication.
"""
from dataclasses import dataclass
from typing import Optional

from src.app.events.base import Query


@dataclass
class PreviewTdeeQuery(Query):
    """Query to preview TDEE calculation without persisting data."""
    age: int
    sex: str  # 'male' or 'female'
    height: float
    weight: float
    job_type: str
    training_days_per_week: int
    training_minutes_per_session: int
    goal: str
    body_fat_percentage: Optional[float] = None
    unit_system: str = "metric"
