"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- SearchFoodsQueryHandler → search_foods_query_handler.py
- GetFoodDetailsQueryHandler → get_food_details_query_handler.py

Please import from individual files or from the module.
"""
from .get_food_details_query_handler import GetFoodDetailsQueryHandler
from .search_foods_query_handler import SearchFoodsQueryHandler

__all__ = ["SearchFoodsQueryHandler", "GetFoodDetailsQueryHandler"]
