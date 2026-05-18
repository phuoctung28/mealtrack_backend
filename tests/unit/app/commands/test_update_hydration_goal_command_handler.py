"""Unit tests for UpdateHydrationGoalCommandHandler."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.api.exceptions import ValidationException
from src.app.commands.hydration.update_hydration_goal_command import (
    UpdateHydrationGoalCommand,
)
from src.app.handlers.command_handlers.update_hydration_goal_command_handler import (
    UpdateHydrationGoalCommandHandler,
)


@pytest.fixture
def handler():
    return UpdateHydrationGoalCommandHandler()


def _mock_uow(new_goal: int):
    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.update_user_hydration_goal = AsyncMock(return_value=new_goal)
    mock_uow.commit = AsyncMock()
    return mock_uow


@pytest.mark.asyncio
async def test_update_goal_at_lower_bound(handler):
    """500 ml (lower bound) is accepted."""
    mock_uow = _mock_uow(500)
    cmd = UpdateHydrationGoalCommand(user_id=str(uuid.uuid4()), goal_ml=500)
    with patch(
        "src.app.handlers.command_handlers.update_hydration_goal_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)
    assert result["goal_ml"] == 500
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_goal_at_upper_bound(handler):
    """4000 ml (upper bound) is accepted."""
    mock_uow = _mock_uow(4000)
    cmd = UpdateHydrationGoalCommand(user_id=str(uuid.uuid4()), goal_ml=4000)
    with patch(
        "src.app.handlers.command_handlers.update_hydration_goal_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)
    assert result["goal_ml"] == 4000


@pytest.mark.asyncio
async def test_update_goal_typical_value(handler):
    """2500 ml mid-range is accepted and DB is updated."""
    mock_uow = _mock_uow(2500)
    cmd = UpdateHydrationGoalCommand(user_id=str(uuid.uuid4()), goal_ml=2500)
    with patch(
        "src.app.handlers.command_handlers.update_hydration_goal_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)
    assert result["goal_ml"] == 2500
    mock_uow.hydration.update_user_hydration_goal.assert_called_once()


@pytest.mark.asyncio
async def test_update_goal_below_minimum_raises_400(handler):
    """Values below 500 are rejected with ValidationException."""
    cmd = UpdateHydrationGoalCommand(user_id=str(uuid.uuid4()), goal_ml=100)
    with pytest.raises(ValidationException) as exc_info:
        await handler.handle(cmd)
    assert exc_info.value.error_code == "INVALID_HYDRATION_GOAL"


@pytest.mark.asyncio
async def test_update_goal_above_maximum_raises_400(handler):
    """Values above 4000 are rejected with ValidationException."""
    for bad_value in (4001, 5000, 6000):
        cmd = UpdateHydrationGoalCommand(user_id=str(uuid.uuid4()), goal_ml=bad_value)
        with pytest.raises(ValidationException):
            await handler.handle(cmd)


@pytest.mark.asyncio
async def test_update_goal_zero_raises_400(handler):
    """0 ml is rejected."""
    cmd = UpdateHydrationGoalCommand(user_id=str(uuid.uuid4()), goal_ml=0)
    with pytest.raises(ValidationException):
        await handler.handle(cmd)
