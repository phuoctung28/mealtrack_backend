"""Handler for fetching workout logs for a user on a specific date."""

import logging
from typing import Any, Dict

from src.app.events.base import EventHandler, handles
from src.app.queries.workout.get_workouts_for_date_query import GetWorkoutsForDateQuery
from src.domain.utils.timezone_utils import resolve_user_timezone_async
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(GetWorkoutsForDateQuery)
class GetWorkoutsForDateQueryHandler(
    EventHandler[GetWorkoutsForDateQuery, Dict[str, Any]]
):
    """Returns workout entries for a user on a local date plus total_burn_kcal."""

    async def handle(self, query: GetWorkoutsForDateQuery) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            user_tz = await resolve_user_timezone_async(
                query.user_id, uow, header_timezone=query.header_timezone
            )
            entries = await uow.workouts.find_for_user_date(
                query.user_id, query.target_date, user_tz
            )

        total_burn: float | None = None
        entry_burns = [e.estimated_burn_kcal for e in entries if e.estimated_burn_kcal is not None]
        if entry_burns:
            total_burn = round(sum(entry_burns), 1)

        return {
            "date": query.target_date.isoformat(),
            "entries": [
                {
                    "id": e.workout_log_id,
                    "workout_type": e.workout_type.value,
                    "intensity": e.intensity.value,
                    "duration_minutes": e.duration_minutes,
                    "estimated_burn_kcal": e.estimated_burn_kcal,
                    "logged_at": e.logged_at.isoformat() if e.logged_at else None,
                    "notes": e.notes,
                }
                for e in entries
            ],
            "total_burn_kcal": total_burn,
        }
