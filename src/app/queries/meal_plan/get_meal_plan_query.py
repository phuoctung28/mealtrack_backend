"""
Get meal plan query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMealPlanQuery(Query):
    """Query to get a meal plan."""
    plan_id: str