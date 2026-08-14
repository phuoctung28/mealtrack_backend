"""Missing hydration deletes must be expected 404s, not ValueError 500s."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.exceptions import ResourceNotFoundException
from src.app.commands.hydration.delete_hydration_entry_command import (
    DeleteHydrationEntryCommand,
)
from src.app.handlers.command_handlers.delete_hydration_entry_command_handler import (
    DeleteHydrationEntryCommandHandler,
)


@pytest.mark.asyncio
async def test_delete_missing_hydration_entry_raises_resource_not_found():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.hydration_entries.find_by_id_or_legacy_meal_id = AsyncMock(return_value=None)
    uow.meals.find_by_id = AsyncMock(return_value=None)

    handler = DeleteHydrationEntryCommandHandler(uow=uow)

    with pytest.raises(ResourceNotFoundException, match="Hydration entry not found"):
        await handler.handle(
            DeleteHydrationEntryCommand(
                user_id="user-1",
                entry_id="hydr_missing",
            )
        )
