"""
Shared cache key definitions and TTL helpers.
"""
from __future__ import annotations

from datetime import date


class CacheKeys:
    """Centralized cache key generator with TTL policies."""

    TTL_10_MIN = 600
    TTL_1_HOUR = 3600
    TTL_1_DAY = 86400
    TTL_7_DAYS = 604_800
    TTL_30_DAYS = 2_592_000

    @staticmethod
    def user_profile(user_id: str) -> tuple[str, int]:
        return (f"user:profile:{user_id}", CacheKeys.TTL_30_DAYS)

    @staticmethod
    def daily_macros(user_id: str, target_date: date) -> tuple[str, int]:
        return (
            f"user:{user_id}:macros:{target_date.isoformat()}",
            CacheKeys.TTL_1_DAY,
        )

    @staticmethod
    def food_search(query: str) -> tuple[str, int]:
        normalized = query.lower().strip()[:64]
        return (f"food:search:{normalized}", CacheKeys.TTL_7_DAYS)

    @staticmethod
    def food_details(food_id: str) -> tuple[str, int]:
        return (f"food:details:{food_id}", CacheKeys.TTL_7_DAYS)

    @staticmethod
    def feature_flag(flag_name: str) -> tuple[str, int]:
        return (f"feature:flag:{flag_name}", CacheKeys.TTL_10_MIN)

    @staticmethod
    def feature_flags() -> tuple[str, int]:
        return ("feature:flags:all", CacheKeys.TTL_10_MIN)

    @staticmethod
    def pattern_for_user(user_id: str) -> str:
        return f"user:{user_id}:*"

