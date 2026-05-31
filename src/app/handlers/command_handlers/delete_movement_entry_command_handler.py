"""Command handler for deleting a movement entry."""

from typing import Optional

from src.api.exceptions import AuthorizationException, ResourceNotFoundException
from src.app.commands.movement import DeleteMovementEntryCommand
from src.app.events.base import EventHandler, handles
from src.app.handlers.command_handlers.log_movement_command_handler import (
    _flush_movement_caches,
)
from src.domain.ports.cache_port import CachePort
from src.domain.utils.timezone_utils import get_zone_info, resolve_user_timezone_async
from src.infra.database.uow_async import AsyncUnitOfWork


@handles(DeleteMovementEntryCommand)
class DeleteMovementEntryCommandHandler(EventHandler[DeleteMovementEntryCommand, dict]):
    def __init__(
        self,
        uow: AsyncUnitOfWork,
        cache_service: Optional[CachePort] = None,
    ):
        self.uow = uow
        self.cache_service = cache_service

    async def handle(self, cmd: DeleteMovementEntryCommand) -> dict:
        async with self.uow as uow:
            entry = await uow.movement_entries.find_by_id(cmd.user_id, cmd.entry_id)
            if not entry:
                raise ResourceNotFoundException(
                    "Movement entry not found", "ENTRY_NOT_FOUND"
                )
            if entry.source == "apple_health":
                raise AuthorizationException(
                    "Apple Health entries cannot be deleted", "APPLE_HEALTH_NOT_EDITABLE"
                )
            user_tz = await resolve_user_timezone_async(cmd.user_id, uow)
            log_date = entry.logged_at.astimezone(get_zone_info(user_tz)).date()
            deleted = await uow.movement_entries.delete(cmd.user_id, cmd.entry_id)
            if not deleted:
                raise ResourceNotFoundException(
                    "Movement entry not found", "ENTRY_NOT_FOUND"
                )

        if self.cache_service:
            await _flush_movement_caches(self.cache_service, cmd.user_id, log_date)

        return {}
