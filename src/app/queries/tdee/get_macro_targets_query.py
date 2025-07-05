"""
Get macro targets query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMacroTargetsQuery(Query):
    """Query to get macro targets based on TDEE and goal."""
    tdee: float
    goal: str
    weight_kg: float