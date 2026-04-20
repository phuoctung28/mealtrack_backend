"""Handler for getting cheat days for a week."""
import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional

from src.app.events.base import EventHandler, handles
from src.app.queries.cheat_day import GetCheatDaysQuery
from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from src.domain.utils.timezone_utils import (
    get_user_monday,
    resolve_user_timezone_async,
    user_today,
)
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(GetCheatDaysQuery)
class GetCheatDaysQueryHandler(EventHandler[GetCheatDaysQuery, Dict[str, Any]]):

    def __init__(self, uow: Optional[UnitOfWorkPort] = None):
        self.uow = uow

    async def handle(self, query: GetCheatDaysQuery) -> Dict[str, Any]:
        uow = self.uow or AsyncUnitOfWork()
        async with uow:
            user_tz = await resolve_user_timezone_async(query.user_id, uow)
            target_date = query.week_of or user_today(user_tz)
            # target_date is already local-date (user timezone), so we can compute Monday
            # without re-fetching timezone from DB.
            week_start = get_user_monday(target_date, query.user_id, uow=None)
            week_end = week_start + timedelta(days=6)

            cheat_days = await uow.cheat_days.find_by_user_and_date_range(
                query.user_id, week_start, week_end
            )

            return {
                "week_start": week_start.isoformat(),
                "cheat_days": [
                    {
                        "date": cd.date.isoformat(),
                        "marked_at": cd.marked_at.isoformat(),
                    }
                    for cd in cheat_days
                ],
            }
