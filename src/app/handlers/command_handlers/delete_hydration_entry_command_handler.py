"""Command handler for soft-deleting a hydration log entry."""

import logging
from typing import Any, Optional

from src.app.commands.hydration.delete_hydration_entry_command import (
    DeleteHydrationEntryCommand,
)
from src.app.events.base import EventHandler, handles
from src.app.events.hydration.hydration_cache_invalidation_required_event import (
    HydrationCacheInvalidationRequiredEvent,
)
from src.app.events.meal.meal_cache_invalidation_required_event import (
    MealCacheInvalidationRequiredEvent,
)
from src.domain.model.meal import MealStatus
from src.domain.ports.cache_port import CachePort
from src.infra.database.uow_async import AsyncUnitOfWork
from src.domain.utils.timezone_utils import (
    resolve_user_timezone_async,
    get_zone_info,
)
from src.app.handlers.command_handlers.log_hydration_command_handler import (
    _flush_hydration_caches,
)

logger = logging.getLogger(__name__)


@handles(DeleteHydrationEntryCommand)
class DeleteHydrationEntryCommandHandler(
    EventHandler[DeleteHydrationEntryCommand, bool]
):
    def __init__(self, uow: AsyncUnitOfWork, event_bus: Any, cache_service: Optional[CachePort] = None):
        self.uow = uow
        self.event_bus = event_bus
        self.cache_service = cache_service

    async def handle(self, cmd: DeleteHydrationEntryCommand) -> bool:
        async with self.uow as uow:
            meal = await uow.meals.find_by_id(cmd.entry_id)
            if meal is None or meal.user_id != cmd.user_id:
                raise ValueError(f"Hydration entry {cmd.entry_id} not found")

            if meal.status != MealStatus.INACTIVE:
                await uow.meals.save(meal.mark_inactive())

            user_tz = await resolve_user_timezone_async(cmd.user_id, uow)
            tz = get_zone_info(user_tz)
            log_date = meal.created_at.astimezone(tz).date()

        if self.cache_service:
            await _flush_hydration_caches(self.cache_service, cmd.user_id, log_date)

        await self.event_bus.publish(
            HydrationCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id,
                user_id=cmd.user_id,
                hydration_date=log_date,
            )
        )
        await self.event_bus.publish(
            MealCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id,
                user_id=cmd.user_id,
                meal_date=log_date,
            )
        )
        return {"success": True}
