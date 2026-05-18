"""Handler for deleting a hydration entry with ownership check."""

import logging
from typing import Any, Dict

from src.api.exceptions import AuthorizationException, ResourceNotFoundException
from src.app.commands.hydration.delete_hydration_command import DeleteHydrationCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteHydrationCommand)
class DeleteHydrationCommandHandler(
    EventHandler[DeleteHydrationCommand, Dict[str, Any]]
):
    """Deletes a hydration entry after verifying the caller owns the record."""

    async def handle(self, command: DeleteHydrationCommand) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            existing = await uow.hydration.find_by_id(command.hydration_entry_id)
            if existing is None:
                raise ResourceNotFoundException(
                    message=f"Hydration entry {command.hydration_entry_id} not found",
                    error_code="HYDRATION_ENTRY_NOT_FOUND",
                )

            if existing.user_id != command.user_id:
                raise AuthorizationException(
                    message="You do not have permission to delete this hydration entry",
                    error_code="HYDRATION_ENTRY_FORBIDDEN",
                )

            deleted = await uow.hydration.delete(
                command.hydration_entry_id, command.user_id
            )
            if not deleted:
                raise ResourceNotFoundException(
                    message=f"Hydration entry {command.hydration_entry_id} not found",
                    error_code="HYDRATION_ENTRY_NOT_FOUND",
                )
            await uow.commit()

        return {"deleted": True}
