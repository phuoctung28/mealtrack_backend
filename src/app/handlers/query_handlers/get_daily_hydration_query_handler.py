"""
GetDailyHydrationQueryHandler — cache-aside handler for daily hydration summary.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

from src.app.events.base import EventHandler, handles
from src.app.queries.hydration.get_daily_hydration_query import GetDailyHydrationQuery
from src.domain.cache.cache_keys import CacheKeys
from src.domain.model.hydration import HydrationEntry, HydrationSummary
from src.domain.services.hydration_catalog_service import find_by_id
from src.domain.utils.timezone_utils import format_iso_utc, get_zone_info, resolve_user_timezone_async
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


def _compute_streak(totals: dict[date, int], today: date, goal_ml: int) -> int:
    """Count consecutive days ending on/before today where consumed_ml >= goal_ml."""
    yesterday = today - timedelta(days=1)
    # Find most recent qualifying day within last 30 days
    most_recent: date | None = None
    for days_back in range(31):
        d = today - timedelta(days=days_back)
        if totals.get(d, 0) >= goal_ml:
            most_recent = d
            break
    if most_recent is None or most_recent < yesterday:
        return 0
    # Count consecutive qualifying days backwards from most_recent
    streak = 0
    current = most_recent
    while current >= today - timedelta(days=30):
        if totals.get(current, 0) >= goal_ml:
            streak += 1
            current -= timedelta(days=1)
        else:
            break
    return streak


def _build_entry_dict(entry: HydrationEntry) -> dict:
    """Enrich a hydration entry with catalog metadata."""
    drink = find_by_id(entry.drink_id)
    return {
        "id": entry.entry_id,
        "drink_id": entry.drink_id,
        "drink_name": drink.name if drink else entry.drink_id,
        "emoji": drink.emoji if drink else "💧",
        "volume_ml": entry.volume_ml,
        "credited_ml": entry.credited_ml,
        "kcal": round(drink.kcal_for_volume(entry.volume_ml), 1) if drink else 0,
        "source": entry.source.value if hasattr(entry.source, "value") else entry.source,
        "meal_id": entry.meal_id,
        "logged_at": format_iso_utc(entry.logged_at),
    }


@handles(GetDailyHydrationQuery)
class GetDailyHydrationQueryHandler(EventHandler[GetDailyHydrationQuery, dict]):
    """Handler for fetching a user's daily hydration summary with cache-aside."""

    def __init__(self, cache_service: Optional[CachePort] = None):
        self.cache_service = cache_service

    async def handle(self, query: GetDailyHydrationQuery) -> dict:
        async with AsyncUnitOfWork() as uow:
            # 1. Resolve timezone
            user_tz_str = await resolve_user_timezone_async(
                query.user_id, uow, query.header_timezone
            )
            user_tz = get_zone_info(user_tz_str)
            target_date: date = query.target_date or datetime.now(user_tz).date()

            # 2. Check cache
            cache_key, ttl = CacheKeys.daily_hydration(query.user_id, target_date)
            if self.cache_service:
                cached = await self.cache_service.get_json(cache_key)
                if cached is not None:
                    return cached

            # 3. Fetch entries from DB
            entries = await uow.hydration_logs.find_by_date(
                query.user_id, target_date, user_tz_str
            )

            # 4. Fetch water goal from user profile
            # TODO: Add daily_water_goal_ml to UserProfileDomainModel and UserProfile ORM
            # when that field is introduced. For now, default to 2000 ml.
            goal_ml = 2000
            try:
                user_profile = await uow.users.get_profile(UUID(query.user_id))
                if user_profile and hasattr(user_profile, "daily_water_goal_ml") and user_profile.daily_water_goal_ml is not None and user_profile.daily_water_goal_ml > 0:
                    goal_ml = user_profile.daily_water_goal_ml
            except Exception:
                logger.debug(
                    "Could not fetch user profile for water goal; defaulting to 2000 ml",
                    exc_info=True,
                )

            # 5. Compute summary
            consumed_ml = sum(e.credited_ml for e in entries)
            summary = HydrationSummary(consumed_ml=consumed_ml, goal_ml=goal_ml)

            # 6. Compute streak (31-day window, single query)
            streak_start = target_date - timedelta(days=30)
            daily_totals = await uow.hydration_logs.sum_credited_ml_by_date_range(
                query.user_id, streak_start, target_date, user_tz_str
            )
            # Merge today's live total in case it differs from cached rows
            daily_totals[target_date] = consumed_ml
            streak = _compute_streak(daily_totals, target_date, goal_ml)

            # 7. Build result dict with enriched entries
            result = {
                "date": target_date.isoformat(),
                "consumed_ml": summary.consumed_ml,
                "goal_ml": summary.goal_ml,
                "percentage": summary.percentage,
                "streak": streak,
                "entries": [
                    _build_entry_dict(e) for e in entries
                ],
            }

        # 7. Cache and return (after UoW context exits so session is closed)
        if self.cache_service:
            await self.cache_service.set_json(cache_key, result, ttl)
        return result
