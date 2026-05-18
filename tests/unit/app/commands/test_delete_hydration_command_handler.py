"""Unit tests for DeleteHydrationCommandHandler."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.api.exceptions import AuthorizationException, ResourceNotFoundException
from src.app.commands.hydration.delete_hydration_command import DeleteHydrationCommand
from src.app.handlers.command_handlers.delete_hydration_command_handler import (
    DeleteHydrationCommandHandler,
)
from src.domain.model.hydration.hydration_entry import DrinkType, HydrationEntry


def _make_entry(user_id: str, entry_id: str | None = None) -> HydrationEntry:
    return HydrationEntry(
        hydration_entry_id=entry_id or str(uuid.uuid4()),
        user_id=user_id,
        drink_type=DrinkType.WATER,
        volume_ml=500,
        logged_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def handler():
    return DeleteHydrationCommandHandler()


@pytest.mark.asyncio
async def test_delete_hydration_happy_path(handler):
    """Owner can delete their own hydration entry."""
    user_id = str(uuid.uuid4())
    entry_id = str(uuid.uuid4())
    entry = _make_entry(user_id=user_id, entry_id=entry_id)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.find_by_id = AsyncMock(return_value=entry)
    mock_uow.hydration.delete = AsyncMock(return_value=True)
    mock_uow.commit = AsyncMock()

    cmd = DeleteHydrationCommand(hydration_entry_id=entry_id, user_id=user_id)
    with patch(
        "src.app.handlers.command_handlers.delete_hydration_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)

    assert result["deleted"] is True
    mock_uow.hydration.delete.assert_called_once_with(entry_id, user_id)
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_hydration_not_found_raises_404(handler):
    """Missing entry raises ResourceNotFoundException."""
    entry_id = str(uuid.uuid4())

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.find_by_id = AsyncMock(return_value=None)

    cmd = DeleteHydrationCommand(
        hydration_entry_id=entry_id, user_id=str(uuid.uuid4())
    )
    with patch(
        "src.app.handlers.command_handlers.delete_hydration_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        with pytest.raises(ResourceNotFoundException):
            await handler.handle(cmd)


@pytest.mark.asyncio
async def test_delete_hydration_wrong_owner_raises_403(handler):
    """Entry belonging to a different user raises AuthorizationException."""
    owner_id = str(uuid.uuid4())
    requester_id = str(uuid.uuid4())
    entry_id = str(uuid.uuid4())
    entry = _make_entry(user_id=owner_id, entry_id=entry_id)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.find_by_id = AsyncMock(return_value=entry)

    cmd = DeleteHydrationCommand(hydration_entry_id=entry_id, user_id=requester_id)
    with patch(
        "src.app.handlers.command_handlers.delete_hydration_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        with pytest.raises(AuthorizationException):
            await handler.handle(cmd)
