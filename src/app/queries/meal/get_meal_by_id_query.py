"""
Get meal by ID query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMealByIdQuery(Query):
    """Query to get a meal by ID."""
    meal_id: str