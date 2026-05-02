"""Handler for deleting a weight entry."""

import logging
from typing import Dict, Any

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.weight import DeleteWeightEntryCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(DeleteWeightEntryCommand)
class DeleteWeightEntryCommandHandler(
    EventHandler[DeleteWeightEntryCommand, Dict[str, Any]]
):
    """Handler for deleting a weight entry."""

    async def handle(self, command: DeleteWeightEntryCommand) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            deleted = await uow.weight_entries.delete(command.user_id, command.entry_id)

            if not deleted:
                raise ResourceNotFoundException(
                    f"Weight entry {command.entry_id} not found"
                )

            await uow.commit()

            return {
                "id": command.entry_id,
                "deleted": True,
                "message": "Weight entry deleted",
            }
