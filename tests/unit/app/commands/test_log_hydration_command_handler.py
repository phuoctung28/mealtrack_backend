"""Unit tests for LogHydrationCommandHandler."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.app.commands.hydration.log_hydration_command import LogHydrationCommand
from src.app.handlers.command_handlers.log_hydration_command_handler import (
    LogHydrationCommandHandler,
)
from src.domain.model.hydration.hydration_entry import DrinkType, HydrationEntry


def _make_entry(user_id: str, volume_ml: int = 500) -> HydrationEntry:
    return HydrationEntry(
        hydration_entry_id=str(uuid.uuid4()),
        user_id=user_id,
        drink_type=DrinkType.WATER,
        volume_ml=volume_ml,
        logged_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def handler():
    return LogHydrationCommandHandler()


@pytest.mark.asyncio
async def test_log_hydration_happy_path(handler):
    """Standard water entry (500 ml) is persisted and returned."""
    user_id = str(uuid.uuid4())
    saved = _make_entry(user_id, volume_ml=500)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.save = AsyncMock(return_value=saved)
    mock_uow.commit = AsyncMock()

    cmd = LogHydrationCommand(
        user_id=user_id,
        drink_type=DrinkType.WATER,
        volume_ml=500,
        logged_at=datetime.now(timezone.utc),
    )
    with patch(
        "src.app.handlers.command_handlers.log_hydration_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)

    assert result["drink_type"] == "WATER"
    assert result["volume_ml"] == 500
    assert result["id"] == saved.hydration_entry_id
    mock_uow.hydration.save.assert_called_once()
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_log_hydration_max_volume(handler):
    """Entry at the 2000 ml boundary is accepted."""
    user_id = str(uuid.uuid4())
    saved = _make_entry(user_id, volume_ml=2000)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.save = AsyncMock(return_value=saved)
    mock_uow.commit = AsyncMock()

    cmd = LogHydrationCommand(
        user_id=user_id,
        drink_type=DrinkType.WATER,
        volume_ml=2000,
        logged_at=datetime.now(timezone.utc),
    )
    with patch(
        "src.app.handlers.command_handlers.log_hydration_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)

    assert result["volume_ml"] == 2000


@pytest.mark.asyncio
async def test_log_hydration_domain_rejects_invalid_volume():
    """Domain model rejects volume > 2000 with ValueError before DB call."""
    with pytest.raises(ValueError, match="volume_ml"):
        HydrationEntry(
            hydration_entry_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            drink_type=DrinkType.WATER,
            volume_ml=3000,  # above max
            logged_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )


@pytest.mark.asyncio
async def test_log_hydration_different_drink_types(handler):
    """BLACK_COFFEE entry is persisted correctly."""
    user_id = str(uuid.uuid4())
    saved = HydrationEntry(
        hydration_entry_id=str(uuid.uuid4()),
        user_id=user_id,
        drink_type=DrinkType.BLACK_COFFEE,
        volume_ml=250,
        logged_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.save = AsyncMock(return_value=saved)
    mock_uow.commit = AsyncMock()

    cmd = LogHydrationCommand(
        user_id=user_id,
        drink_type=DrinkType.BLACK_COFFEE,
        volume_ml=250,
        logged_at=datetime.now(timezone.utc),
    )
    with patch(
        "src.app.handlers.command_handlers.log_hydration_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)

    assert result["drink_type"] == "BLACK_COFFEE"
    assert result["volume_ml"] == 250
