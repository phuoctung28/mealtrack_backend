"""
Get meal suggestions for profile query.
"""
from dataclasses import dataclass

from src.app.events.base import Query


@dataclass
class GetMealSuggestionsForProfileQuery(Query):
    """Query to get meal suggestions for a user profile."""
    user_profile_id: str