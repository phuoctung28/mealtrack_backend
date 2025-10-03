"""
Meal queries.
"""
from .get_daily_macros_query import GetDailyMacrosQuery
from .get_meal_by_id_query import GetMealByIdQuery

__all__ = [
    "GetMealByIdQuery",
    "GetDailyMacrosQuery",
]