"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- GetConversationHistoryQueryHandler → get_conversation_history_query_handler.py
- GetMealPlanQueryHandler → get_meal_plan_query_handler.py
- GetMealsByDateQueryHandler → get_meals_by_date_meal_plan_query_handler.py

Please import from individual files or from the module.
"""
from .get_conversation_history_query_handler import GetConversationHistoryQueryHandler
from .get_meal_plan_query_handler import GetMealPlanQueryHandler
from .get_meals_by_date_meal_plan_query_handler import GetMealsByDateQueryHandler

__all__ = [
    "GetConversationHistoryQueryHandler",
    "GetMealPlanQueryHandler",
    "GetMealsByDateQueryHandler"
]
