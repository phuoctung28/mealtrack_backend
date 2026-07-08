"""Compatibility import path for meal value insight scheduling helpers."""

from src.app.services.meal_value_insight_scheduler import (
    build_value_insights_for_meal,
    build_value_insights_for_meal_with_profile,
    compact_meal_insight_user_context,
    get_meal_insight_user_context,
    schedule_value_insight_generation,
)

__all__ = [
    "build_value_insights_for_meal",
    "build_value_insights_for_meal_with_profile",
    "compact_meal_insight_user_context",
    "get_meal_insight_user_context",
    "schedule_value_insight_generation",
]
