"""
Compare TDEE methods query.
"""
from dataclasses import dataclass
from typing import Optional

from src.app.events.base import Query


@dataclass
class CompareTdeeMethodsQuery(Query):
    """Query to compare different TDEE calculation methods."""
    age: int
    sex: str
    height_cm: float
    weight_kg: float
    activity_level: str
    body_fat_percentage: Optional[float] = None