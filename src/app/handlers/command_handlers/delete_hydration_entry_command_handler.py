"""Command handler for soft-deleting a hydration log entry."""

import logging
from typing import Any

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
from src.infra.database.uow_async import AsyncUnitOfWork
from src.domain.utils.timezone_utils import (
    resolve_user_timezone_async,
    get_zone_info,
)

logger = logging.getLogger(__name__)


@handles(DeleteHydrationEntryCommand)
class DeleteHydrationEntryCommandHandler(
    EventHandler[DeleteHydrationEntryCommand, bool]
):
    def __init__(self, uow: AsyncUnitOfWork, event_bus: Any):
        self.uow = uow
        self.event_bus = event_bus

    async def handle(self, cmd: DeleteHydrationEntryCommand) -> bool:
        async with self.uow as uow:
            entry = await uow.hydration_logs.find_by_id(cmd.user_id, cmd.entry_id)
            if entry is None:
                raise ValueError(f"Hydration entry {cmd.entry_id} not found")

            await uow.hydration_logs.soft_delete(cmd.user_id, cmd.entry_id)

            # If linked to a meal, also soft-delete the meal
            if entry.meal_id:
                meal = await uow.meals.find_by_id(entry.meal_id)
                if meal and meal.status != MealStatus.INACTIVE:
                    await uow.meals.save(meal.mark_inactive())

            # Resolve date for cache invalidation
            user_tz = await resolve_user_timezone_async(cmd.user_id, uow)
            tz = get_zone_info(user_tz)
            log_date = entry.logged_at.astimezone(tz).date()

        # Publish cache invalidation for hydration cache
        await self.event_bus.publish(
            HydrationCacheInvalidationRequiredEvent(
                aggregate_id=cmd.user_id,
                user_id=cmd.user_id,
                hydration_date=log_date,
            )
        )
        # If linked to a meal, also invalidate meal cache
        if entry.meal_id:
            await self.event_bus.publish(
                MealCacheInvalidationRequiredEvent(
                    aggregate_id=cmd.user_id,
                    user_id=cmd.user_id,
                    meal_date=log_date,
                )
            )
        return {"success": True}
