"""
DEPRECATED: Backward compatibility shim.

All handlers extracted to individual files:
- GetDailyActivitiesQueryHandler → get_daily_activities_query_handler.py

Please import from individual files or from the module.
"""
from .get_daily_activities_query_handler import GetDailyActivitiesQueryHandler

__all__ = ["GetDailyActivitiesQueryHandler"]
