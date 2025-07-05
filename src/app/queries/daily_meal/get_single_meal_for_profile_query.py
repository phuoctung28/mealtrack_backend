"""
Get single meal for profile query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetSingleMealForProfileQuery(Query):
    """Query to get a single meal suggestion for a profile."""
    user_profile_id: str
    meal_type: str