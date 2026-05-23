"""
GetWeeklyHydrationQueryHandler — 7-day hydration chart data.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

from src.app.events.base import EventHandler, handles
from src.app.queries.hydration.get_weekly_hydration_query import GetWeeklyHydrationQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.ports.cache_port import CachePort
from src.domain.services.hydration_goal_service import resolve_hydration_goal_ml
from src.domain.utils.timezone_utils import get_zone_info, resolve_user_timezone_async
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


def _monday_of_week(d: date) -> date:
    """Return the Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


@handles(GetWeeklyHydrationQuery)
class GetWeeklyHydrationQueryHandler(EventHandler[GetWeeklyHydrationQuery, dict]):
    """Handler for fetching a 7-day hydration summary with cache-aside."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetWeeklyHydrationQuery) -> dict:
        async with AsyncUnitOfWork() as uow:
            user_tz_str = await resolve_user_timezone_async(
                query.user_id, uow, query.header_timezone
            )
            user_tz = get_zone_info(user_tz_str)
            today = datetime.now(user_tz).date()

            week_start: date = query.start_date or _monday_of_week(today)
            week_end = week_start + timedelta(days=6)

            cache_key, ttl = CacheKeys.weekly_hydration(query.user_id, week_start)
            if self.cache_service:
                cached = await self.cache_service.get_json(cache_key)
                if cached is not None:
                    return cached

            goal_ml = 2000
            try:
                user_profile = await uow.users.get_profile(UUID(query.user_id))
                if user_profile:
                    goal_ml = resolve_hydration_goal_ml(user_profile)
            except Exception:
                logger.debug("Could not fetch user profile for water goal; defaulting to 2000 ml", exc_info=True)

            daily_totals = await uow.hydration_logs.sum_credited_ml_by_date_range(
                query.user_id, week_start, week_end, user_tz_str
            )

        days = []
        current = week_start
        while current <= week_end:
            days.append({"date": current.isoformat(), "consumed_ml": daily_totals.get(current, 0)})
            current += timedelta(days=1)

        result = {
            "week_start": week_start.isoformat(),
            "days": days,
            "goal_ml": goal_ml,
        }

        if self.cache_service:
            await self.cache_service.set_json(cache_key, result, ttl)
        return result
