"""
Handler for activities presence query - returns boolean map of dates with meals.
"""
import logging
from datetime import date, timedelta
from typing import Dict, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.nutrition import GetActivitiesPresenceQuery
from src.domain.utils.timezone_utils import resolve_user_timezone_async
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)

MAX_DATE_RANGE = 60


@handles(GetActivitiesPresenceQuery)
class GetActivitiesPresenceQueryHandler(EventHandler[GetActivitiesPresenceQuery, Dict[str, bool]]):
    """Handler for activities presence check."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetActivitiesPresenceQuery) -> Dict[str, bool]:
        """Return boolean map indicating which dates have meals."""
        if (query.end_date - query.start_date).days > MAX_DATE_RANGE:
            raise ValueError(f"Date range cannot exceed {MAX_DATE_RANGE} days")

        async with AsyncUnitOfWork() as uow:
            user_tz_str = await resolve_user_timezone_async(
                query.user_id, uow, query.header_timezone
            )

            daily_counts = await uow.meals.get_daily_meal_counts(
                query.user_id,
                query.start_date,
                query.end_date,
                user_timezone=user_tz_str,
            )

            result: Dict[str, bool] = {}
            current = query.start_date
            while current <= query.end_date:
                result[current.isoformat()] = current in daily_counts and daily_counts[current] > 0
                current += timedelta(days=1)

            return result
