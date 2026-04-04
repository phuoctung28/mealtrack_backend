"""
GetStreakQueryHandler — computes current and best logging streak.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.meal.get_streak_query import GetStreakQuery
from src.domain.utils.timezone_utils import get_zone_info, resolve_user_timezone
from src.infra.database.uow import UnitOfWork

logger = logging.getLogger(__name__)


@handles(GetStreakQuery)
class GetStreakQueryHandler(EventHandler[GetStreakQuery, Dict[str, Any]]):
    """Handler that calculates current + best logging streak for a user."""

    async def handle(self, query: GetStreakQuery) -> Dict[str, Any]:
        """Return current_streak, best_streak, and last_logged_date."""
        with UnitOfWork() as uow:
            user_tz_str = resolve_user_timezone(
                query.user_id, uow, query.header_timezone
            )
            user_tz = get_zone_info(user_tz_str)
            today = datetime.now(user_tz).date()

            dates = uow.meals.get_dates_with_meals(
                query.user_id, user_timezone=user_tz_str
            )
            scan_count = uow.meals.count_by_source(query.user_id, "scanner")

        if not dates:
            return {"current_streak": 0, "best_streak": 0, "last_logged_date": None, "scan_count": scan_count}

        last_logged = dates[0]

        current_streak = self._calculate_current_streak(dates, today)
        best_streak = self._calculate_best_streak(dates)

        return {
            "current_streak": current_streak,
            "best_streak": best_streak,
            "last_logged_date": last_logged.isoformat(),
            "scan_count": scan_count,
        }

    def _calculate_current_streak(self, dates: list[date], today: date) -> int:
        """Walk backwards from today; streak not broken until day ends."""
        if not dates:
            return 0

        # Allow streak to start from today or yesterday (streak not broken until day ends)
        cursor = today if today in dates else today - timedelta(days=1)
        if cursor not in dates:
            return 0

        date_set = set(dates)
        streak = 0
        while cursor in date_set:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def _calculate_best_streak(self, dates: list[date]) -> int:
        """Find the longest consecutive run across all logged dates."""
        if not dates:
            return 0

        date_set = set(dates)
        best = 0
        for d in date_set:
            # Only start counting from a "streak start" (day before not in set)
            if (d - timedelta(days=1)) not in date_set:
                length = 0
                cursor = d
                while cursor in date_set:
                    length += 1
                    cursor += timedelta(days=1)
                best = max(best, length)
        return best
