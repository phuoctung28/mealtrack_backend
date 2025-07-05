"""
Search meals query.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from src.app.events.base import Query


@dataclass
class SearchMealsQuery(Query):
    """Query to search meals."""
    dish_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_calories: Optional[float] = None
    max_calories: Optional[float] = None