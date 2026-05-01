"""Handler for syncing weight entries from mobile."""

import logging
import uuid
from typing import Dict, Any

from src.app.commands.weight import SyncWeightEntriesCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.weight import WeightEntry
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(SyncWeightEntriesCommand)
class SyncWeightEntriesCommandHandler(
    EventHandler[SyncWeightEntriesCommand, Dict[str, Any]]
):
    """Handler for bulk syncing weight entries."""

    async def handle(self, command: SyncWeightEntriesCommand) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            entries = [
                WeightEntry(
                    id=str(uuid.uuid4()),
                    user_id=command.user_id,
                    weight_kg=e.weight_kg,
                    recorded_at=e.recorded_at,
                )
                for e in command.entries
            ]

            synced = await uow.weight_entries.bulk_upsert(command.user_id, entries)
            await uow.commit()

            return {
                "synced_count": synced,
                "message": f"Synced {synced} weight entries",
            }
