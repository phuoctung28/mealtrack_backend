"""Unit tests for DeleteWorkoutCommandHandler."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.api.exceptions import AuthorizationException, ResourceNotFoundException
from src.app.commands.workout.delete_workout_command import DeleteWorkoutCommand
from src.app.handlers.command_handlers.delete_workout_command_handler import (
    DeleteWorkoutCommandHandler,
)
from src.domain.model.workout.workout_log import Intensity, WorkoutLog, WorkoutType


def _make_log(user_id: str, log_id: str | None = None):
    lid = log_id or str(uuid.uuid4())
    return WorkoutLog(
        workout_log_id=lid,
        user_id=user_id,
        workout_type=WorkoutType.RUNNING,
        intensity=Intensity.MODERATE,
        duration_minutes=30,
        logged_at=datetime.now(timezone.utc),
        met_value=8.3,
        weight_kg_snapshot=None,
        estimated_burn_kcal=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def handler():
    return DeleteWorkoutCommandHandler()


@pytest.mark.asyncio
async def test_delete_workout_happy_path(handler):
    """Owner can delete their own workout log."""
    user_id = str(uuid.uuid4())
    log_id = str(uuid.uuid4())
    log = _make_log(user_id=user_id, log_id=log_id)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.workouts.find_by_id = AsyncMock(return_value=log)
    mock_uow.workouts.delete = AsyncMock(return_value=True)
    mock_uow.commit = AsyncMock()

    cmd = DeleteWorkoutCommand(workout_log_id=log_id, user_id=user_id)
    with patch(
        "src.app.handlers.command_handlers.delete_workout_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)

    assert result["deleted"] is True
    mock_uow.workouts.delete.assert_called_once_with(log_id, user_id)
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_workout_not_found_raises_404(handler):
    """Missing log raises ResourceNotFoundException."""
    log_id = str(uuid.uuid4())

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.workouts.find_by_id = AsyncMock(return_value=None)

    cmd = DeleteWorkoutCommand(workout_log_id=log_id, user_id=str(uuid.uuid4()))
    with patch(
        "src.app.handlers.command_handlers.delete_workout_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        with pytest.raises(ResourceNotFoundException):
            await handler.handle(cmd)


@pytest.mark.asyncio
async def test_delete_workout_wrong_owner_raises_403(handler):
    """Log belonging to a different user raises AuthorizationException."""
    owner_id = str(uuid.uuid4())
    requester_id = str(uuid.uuid4())
    log_id = str(uuid.uuid4())
    log = _make_log(user_id=owner_id, log_id=log_id)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.workouts.find_by_id = AsyncMock(return_value=log)

    cmd = DeleteWorkoutCommand(workout_log_id=log_id, user_id=requester_id)
    with patch(
        "src.app.handlers.command_handlers.delete_workout_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        with pytest.raises(AuthorizationException):
            await handler.handle(cmd)
