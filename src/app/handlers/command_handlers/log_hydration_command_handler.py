"""Command handler for logging a hydration (non-caloric) drink entry."""

import logging
from typing import Any

from src.app.commands.hydration.log_hydration_command import LogHydrationCommand
from src.app.events.base import EventHandler, handles
from src.app.events.hydration.hydration_cache_invalidation_required_event import (
    HydrationCacheInvalidationRequiredEvent,
)
from src.domain.model.hydration import HydrationEntry, DrinkCategory, HydrationSource
from src.domain.services.hydration_catalog_service import find_by_id
from src.infra.database.uow_async import AsyncUnitOfWork
from src.domain.utils.timezone_utils import (
    utc_now,
    noon_utc_for_date,
    resolve_user_timezone_async,
    get_zone_info,
)

logger = logging.getLogger(__name__)


@handles(LogHydrationCommand)
class LogHydrationCommandHandler(EventHandler[LogHydrationCommand, HydrationEntry]):
    def __init__(self, uow: AsyncUnitOfWork, event_bus: Any):
        self.uow = uow
        self.event_bus = event_bus

    async def handle(self, cmd: LogHydrationCommand) -> HydrationEntry:
        # 1. Validate drink_id exists in catalog and is category "hydration"
        drink = find_by_id(cmd.drink_id)
        if drink is None:
            raise ValueError(f"Unknown drink: {cmd.drink_id}")
        if drink.category != DrinkCategory.HYDRATION:
            raise ValueError(
                f"Drink {cmd.drink_id} is caloric — use LogCaloricDrinkCommand"
            )

        # 2. Resolve the log date (timezone-aware)
        async with self.uow as uow:
            now = utc_now()
            if cmd.target_date:
                user_tz = await resolve_user_timezone_async(
                    cmd.user_id, uow, cmd.header_timezone
                )
                log_date = cmd.target_date
                log_dt = noon_utc_for_date(log_date, user_tz)
            else:
                log_dt = now
                user_tz = await resolve_user_timezone_async(
                    cmd.user_id, uow, cmd.header_timezone
                )
                tz = get_zone_info(user_tz)
                log_date = log_dt.astimezone(tz).date()

            # 3. Create and save HydrationEntry
            credited_ml = drink.credited_ml_for_volume(cmd.volume_ml)
            # First create via factory to get a valid entry_id / created_at
            prototype = HydrationEntry.create(
                user_id=cmd.user_id,
                drink_id=cmd.drink_id,
                volume_ml=cmd.volume_ml,
                credited_ml=credited_ml,
                source=HydrationSource.HYDRATION,
            )
            # Override logged_at with the resolved datetime.
            # Reconstruct with timezone-resolved logged_at
            entry = HydrationEntry(
                entry_id=prototype.entry_id,
                user_id=prototype.user_id,
                drink_id=prototype.drink_id,
                volume_ml=prototype.volume_ml,
                credited_ml=prototype.credited_ml,
                source=prototype.source,
                meal_id=None,
                logged_at=log_dt,
                created_at=prototype.created_at,
                is_deleted=False,
            )
            saved = await uow.hydration_logs.save(entry)

        # 4. Publish cache invalidation event
        await self.event_bus.publish(
            HydrationCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id,
                user_id=cmd.user_id,
                hydration_date=log_date,
            )
        )
        return saved
