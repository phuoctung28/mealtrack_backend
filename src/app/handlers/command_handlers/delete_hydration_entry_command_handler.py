"""Command handler for soft-deleting a hydration log entry."""

import logging
from typing import Optional

from src.app.commands.hydration.delete_hydration_entry_command import (
    DeleteHydrationEntryCommand,
)
from src.app.events.base import EventHandler, handles
from src.app.services.cache_invalidation_service import CacheInvalidationService
from src.domain.model.meal import MealStatus
from src.infra.database.uow_async import AsyncUnitOfWork
from src.domain.utils.timezone_utils import (
    resolve_user_timezone_async,
    get_zone_info,
)

logger = logging.getLogger(__name__)


@handles(DeleteHydrationEntryCommand)
class DeleteHydrationEntryCommandHandler(
    EventHandler[DeleteHydrationEntryCommand, dict]
):
    def __init__(
        self,
        uow: AsyncUnitOfWork,
        cache_invalidation: Optional[CacheInvalidationService] = None,
    ):
        self.uow = uow
        self.cache_invalidation = cache_invalidation

    async def handle(self, cmd: DeleteHydrationEntryCommand) -> dict:
        async with self.uow as uow:
            meal = await uow.meals.find_by_id(cmd.entry_id)
            if meal is None or meal.user_id != cmd.user_id:
                raise ValueError("Hydration entry not found")
            if meal.meal_type != "hydration":
                raise ValueError("Hydration entry not found")

            if meal.status != MealStatus.INACTIVE:
                await uow.meals.save(meal.mark_inactive())

            user_tz = await resolve_user_timezone_async(cmd.user_id, uow)
            tz = get_zone_info(user_tz)
            log_date = meal.created_at.astimezone(tz).date()

        # Synchronous invalidation guarantees Redis is cleared before the response returns
        if self.cache_invalidation:
            await self.cache_invalidation.after_hydration_write(cmd.user_id, log_date)

        return {"success": True}
