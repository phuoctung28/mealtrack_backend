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
    activity_level: str
    goal: str
    body_fat_percentage: Optional[float] = None
    unit_system: str = "metric"
