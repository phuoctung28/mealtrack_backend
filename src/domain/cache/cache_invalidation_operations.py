"""Pure cache invalidation operation builders."""

from __future__ import annotations

from datetime import date, timedelta

from src.domain.cache.cache_keys import CacheKeys

DELETE_KEY = "delete_key"
DELETE_PATTERN = "delete_pattern"


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def build_meal_invalidation_operations(
    user_id: str,
    meal_date: date,
    *,
    current_date: date | None = None,
) -> list[dict[str, str]]:
    """Build the exact cache deletes currently used after a meal write."""
    meal_week_start = _week_start(meal_date)
    current_week_start = _week_start(current_date or date.today())

    operations: list[dict[str, str]] = [
        {
            "op": DELETE_PATTERN,
            "pattern": f"user:{user_id}:activities:{meal_date.isoformat()}:*",
        },
        {
            "op": DELETE_KEY,
            "key": CacheKeys.daily_macros(user_id, meal_date)[0],
        },
        {
            "op": DELETE_KEY,
            "key": CacheKeys.weekly_budget(user_id, meal_week_start)[0],
        },
        {
            "op": DELETE_PATTERN,
            "pattern": CacheKeys.weekly_budget_pattern(user_id, meal_week_start),
        },
        {
            "op": DELETE_PATTERN,
            "pattern": f"user:{user_id}:nutrition_bulk:*",
        },
        {
            "op": DELETE_KEY,
            "key": CacheKeys.daily_breakdown(user_id, meal_week_start)[0],
        },
        {
            "op": DELETE_KEY,
            "key": CacheKeys.user_streak(user_id)[0],
        },
    ]

    if meal_week_start != current_week_start:
        operations.extend(
            [
                {
                    "op": DELETE_KEY,
                    "key": CacheKeys.weekly_budget(user_id, current_week_start)[0],
                },
                {
                    "op": DELETE_PATTERN,
                    "pattern": CacheKeys.weekly_budget_pattern(
                        user_id, current_week_start
                    ),
                },
                {
                    "op": DELETE_KEY,
                    "key": CacheKeys.daily_breakdown(user_id, current_week_start)[0],
                },
            ]
        )

    return operations
