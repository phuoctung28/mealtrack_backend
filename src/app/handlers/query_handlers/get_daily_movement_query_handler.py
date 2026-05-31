"""Query handler for daily movement summary."""

from datetime import datetime, time, timedelta, timezone

from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.log_movement_command_handler import (
    _movement_response,
)
from src.app.queries.movement import GetDailyMovementQuery
from src.domain.utils.timezone_utils import (
    get_zone_info,
    resolve_user_timezone_async,
    user_today,
)
from src.infra.database.uow_async import AsyncUnitOfWork


def _local_day_utc_range(target_date, user_tz_str: str) -> tuple[datetime, datetime]:
    user_tz = get_zone_info(user_tz_str)
    local_start = datetime.combine(target_date, time.min, tzinfo=user_tz)
    local_end = local_start + timedelta(days=1)
    return (
        local_start.astimezone(timezone.utc),
        local_end.astimezone(timezone.utc),
    )


@handles(GetDailyMovementQuery)
class GetDailyMovementQueryHandler(EventHandler[GetDailyMovementQuery, dict]):
    def __init__(self, uow: AsyncUnitOfWork = None):
        self._uow = uow

    async def handle(self, query: GetDailyMovementQuery) -> dict:
        async with (self._uow if self._uow is not None else AsyncUnitOfWork()) as uow:
            user_tz = await resolve_user_timezone_async(
                query.user_id, uow, query.header_timezone
            )
            target_date = query.target_date or user_today(user_tz)
            start_utc, end_utc = _local_day_utc_range(target_date, user_tz)
            entries = await uow.movement_entries.find_by_user_and_logged_range(
                query.user_id, start_utc, end_utc
            )

        return {
            "date": target_date.isoformat(),
            "goal_kcal": 300.0,
            "entries": [_movement_response(entry) for entry in entries],
        }
