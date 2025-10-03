"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- GetUserTdeeQueryHandler → get_user_tdee_query_handler.py

Please import from individual files or from the module.
"""
from .get_user_tdee_query_handler import GetUserTdeeQueryHandler

__all__ = ["GetUserTdeeQueryHandler"]
