"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- GetMealByIdQueryHandler → get_meal_by_id_query_handler.py
- GetMealsByDateQueryHandler → get_meals_by_date_query_handler.py
- GetDailyMacrosQueryHandler → get_daily_macros_query_handler.py

Please import from individual files or from the module.
"""
from .get_daily_macros_query_handler import GetDailyMacrosQueryHandler
from .get_meal_by_id_query_handler import GetMealByIdQueryHandler
from .get_meals_by_date_query_handler import GetMealsByDateQueryHandler

__all__ = [
    "GetMealByIdQueryHandler",
    "GetMealsByDateQueryHandler",
    "GetDailyMacrosQueryHandler"
]
