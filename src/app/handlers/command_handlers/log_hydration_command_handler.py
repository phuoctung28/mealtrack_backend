"""Handler for logging a hydration entry."""

import logging
from typing import Any, Dict

from src.app.commands.hydration.log_hydration_command import LogHydrationCommand
from src.app.events.base import EventHandler, handles
from src.domain.model.hydration.hydration_entry import HydrationEntry
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(LogHydrationCommand)
class LogHydrationCommandHandler(EventHandler[LogHydrationCommand, Dict[str, Any]]):
    """Persists a new hydration entry. Volume bounds (1–2000 ml) are enforced at the API
    Pydantic layer; domain __post_init__ provides a final safety net."""

    async def handle(self, command: LogHydrationCommand) -> Dict[str, Any]:
        async with AsyncUnitOfWork() as uow:
            entry = HydrationEntry.create_new(
                user_id=command.user_id,
                drink_type=command.drink_type,
                volume_ml=command.volume_ml,
                logged_at=command.logged_at,
            )
            saved = await uow.hydration.save(entry)
            await uow.commit()

            return {
                "id": saved.hydration_entry_id,
                "drink_type": saved.drink_type.value,
                "volume_ml": saved.volume_ml,
                "logged_at": saved.logged_at.isoformat() if saved.logged_at else None,
                "created_at": saved.created_at.isoformat() if saved.created_at else None,
            }
