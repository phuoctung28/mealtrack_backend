"""Unit tests: timezone update handler skips DB write when tz is unchanged."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.app.commands.user.update_timezone_command import UpdateTimezoneCommand
from src.app.handlers.command_handlers.update_timezone_command_handler import (
    UpdateTimezoneCommandHandler,
)


@pytest.mark.asyncio
async def test_skips_db_write_when_timezone_unchanged():
    """If the stored timezone equals the incoming one, no DB write occurs."""
    handler = UpdateTimezoneCommandHandler()
    command = UpdateTimezoneCommand(user_id="user-1", timezone="Asia/Ho_Chi_Minh")

    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users.get_user_timezone = AsyncMock(return_value="Asia/Ho_Chi_Minh")  # same
    mock_uow.users.update_user_timezone = AsyncMock()

    with patch(
        "src.app.handlers.command_handlers.update_timezone_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(command)

    assert result == {"success": True, "timezone": "Asia/Ho_Chi_Minh"}
    mock_uow.users.update_user_timezone.assert_not_called()
    # commit() may be called by the read-path UoW's __exit__ — we only assert the write didn't happen


@pytest.mark.asyncio
async def test_writes_db_when_timezone_changed():
    """If the stored timezone differs, the update proceeds."""
    handler = UpdateTimezoneCommandHandler()
    command = UpdateTimezoneCommand(user_id="user-1", timezone="America/New_York")

    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users.get_user_timezone = AsyncMock(return_value="UTC")  # different
    mock_uow.users.update_user_timezone = AsyncMock()
    mock_uow.commit = AsyncMock()

    with patch(
        "src.app.handlers.command_handlers.update_timezone_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(command)

    assert result["success"] is True
    mock_uow.users.update_user_timezone.assert_called_once_with("user-1", "America/New_York")


@pytest.mark.asyncio
async def test_writes_db_when_no_stored_timezone():
    """If no timezone is stored yet (None), the update proceeds."""
    handler = UpdateTimezoneCommandHandler()
    command = UpdateTimezoneCommand(user_id="user-1", timezone="Asia/Ho_Chi_Minh")

    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users.get_user_timezone = AsyncMock(return_value=None)
    mock_uow.users.update_user_timezone = AsyncMock()
    mock_uow.commit = AsyncMock()

    with patch(
        "src.app.handlers.command_handlers.update_timezone_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(command)

    assert result["success"] is True
    mock_uow.users.update_user_timezone.assert_called_once_with("user-1", "Asia/Ho_Chi_Minh")
