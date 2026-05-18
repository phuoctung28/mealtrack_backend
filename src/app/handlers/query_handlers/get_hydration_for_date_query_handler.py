"""Handler for fetching hydration entries for a user on a specific date."""

import logging
from typing import Any, Dict

from src.app.events.base import EventHandler, handles
from src.app.queries.hydration.get_hydration_for_date_query import (
    GetHydrationForDateQuery,
)
from src.domain.utils.timezone_utils import resolve_user_timezone_async
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(GetHydrationForDateQuery)
class GetHydrationForDateQueryHandler(
    EventHandler[GetHydrationForDateQuery, Dict[str, Any]]
):
    """Returns hydration entries for a user on a local date plus goal_ml and total_ml."""

    async def handle(self, query: GetHydrationForDateQuery) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            user_tz = await resolve_user_timezone_async(
                query.user_id, uow, header_timezone=query.header_timezone
            )
            entries = await uow.hydration.find_for_user_date(
                query.user_id, query.target_date, user_tz
            )
            goal_ml = await uow.hydration.get_user_hydration_goal(query.user_id)

        total_ml = sum(e.volume_ml for e in entries)

        return {
            "date": query.target_date.isoformat(),
            "goal_ml": goal_ml,
            "total_ml": total_ml,
            "entries": [
                {
                    "id": e.hydration_entry_id,
                    "drink_type": e.drink_type.value,
                    "volume_ml": e.volume_ml,
                    "logged_at": e.logged_at.isoformat() if e.logged_at else None,
                }
                for e in entries
            ],
        }
