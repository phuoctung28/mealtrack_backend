"""Command handler for deleting a movement entry."""

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.movement import DeleteMovementEntryCommand
from src.app.events.base import EventHandler, handles
from src.infra.database.uow_async import AsyncUnitOfWork


@handles(DeleteMovementEntryCommand)
class DeleteMovementEntryCommandHandler(EventHandler[DeleteMovementEntryCommand, dict]):
    def __init__(self, uow: AsyncUnitOfWork):
        self.uow = uow

    async def handle(self, cmd: DeleteMovementEntryCommand) -> dict:
        async with self.uow as uow:
            deleted = await uow.movement_entries.delete(cmd.user_id, cmd.entry_id)
            if not deleted:
                raise ResourceNotFoundException(
                    "Movement entry not found", "ENTRY_NOT_FOUND"
                )
            await uow.commit()

        return {}
