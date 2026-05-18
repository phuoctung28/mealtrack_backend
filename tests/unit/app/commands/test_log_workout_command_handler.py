"""Unit tests for LogWorkoutCommandHandler."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.commands.workout.log_workout_command import LogWorkoutCommand
from src.app.handlers.command_handlers.log_workout_command_handler import (
    LogWorkoutCommandHandler,
)
from src.domain.model.workout.workout_log import Intensity, WorkoutLog, WorkoutType


def _make_user(weight_kg=75.0):
    """Build a minimal mock UserDomainModel."""
    user = MagicMock()
    if weight_kg is not None:
        profile = MagicMock()
        profile.weight_kg = weight_kg
        user.current_profile = profile
    else:
        user.current_profile = None
    return user


def _make_log(**kwargs):
    """Build a WorkoutLog domain object for mock returns."""
    defaults = dict(
        workout_log_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        workout_type=WorkoutType.RUNNING,
        intensity=Intensity.MODERATE,
        duration_minutes=45,
        logged_at=datetime.now(timezone.utc),
        met_value=8.3,
        weight_kg_snapshot=75.0,
        estimated_burn_kcal=466.9,
        notes=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return WorkoutLog(**defaults)


@pytest.fixture
def handler():
    return LogWorkoutCommandHandler()


@pytest.fixture
def base_command():
    return LogWorkoutCommand(
        user_id=str(uuid.uuid4()),
        workout_type=WorkoutType.RUNNING,
        intensity=Intensity.MODERATE,
        duration_minutes=45,
        logged_at=datetime.now(timezone.utc),
        notes="test run",
    )


@pytest.mark.asyncio
async def test_log_workout_happy_path_with_weight(handler, base_command):
    """Handler computes burn kcal when user has a weight snapshot."""
    user = _make_user(weight_kg=75.0)
    saved_log = _make_log(
        user_id=base_command.user_id,
        estimated_burn_kcal=466.9,
        notes=base_command.notes,
    )

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users.find_by_id = AsyncMock(return_value=user)
    mock_uow.workouts.save = AsyncMock(return_value=saved_log)
    mock_uow.commit = AsyncMock()

    with patch(
        "src.app.handlers.command_handlers.log_workout_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(base_command)

    assert result["estimated_burn_kcal"] == 466.9
    assert result["workout_type"] == "RUNNING"
    assert result["intensity"] == "MODERATE"
    assert result["duration_minutes"] == 45
    mock_uow.workouts.save.assert_called_once()
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_log_workout_no_weight_returns_null_burn(handler, base_command):
    """Handler returns estimated_burn_kcal=None when user has no weight."""
    user = _make_user(weight_kg=None)
    saved_log = _make_log(
        user_id=base_command.user_id,
        weight_kg_snapshot=None,
        estimated_burn_kcal=None,
    )

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users.find_by_id = AsyncMock(return_value=user)
    mock_uow.workouts.save = AsyncMock(return_value=saved_log)
    mock_uow.commit = AsyncMock()

    with patch(
        "src.app.handlers.command_handlers.log_workout_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(base_command)

    assert result["estimated_burn_kcal"] is None


@pytest.mark.asyncio
async def test_log_workout_user_not_found_still_saves(handler, base_command):
    """When the user record is missing, burn is None but save proceeds."""
    saved_log = _make_log(
        user_id=base_command.user_id,
        weight_kg_snapshot=None,
        estimated_burn_kcal=None,
    )

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users.find_by_id = AsyncMock(return_value=None)
    mock_uow.workouts.save = AsyncMock(return_value=saved_log)
    mock_uow.commit = AsyncMock()

    with patch(
        "src.app.handlers.command_handlers.log_workout_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(base_command)

    assert result["estimated_burn_kcal"] is None
    mock_uow.workouts.save.assert_called_once()


@pytest.mark.asyncio
async def test_log_workout_hiit_vigorous(handler):
    """HIIT VIGOROUS uses MET 12.0 correctly."""
    user = _make_user(weight_kg=80.0)
    # kcal = 12.0 * 80 * (30/60) = 480.0
    saved_log = _make_log(
        workout_type=WorkoutType.HIIT,
        intensity=Intensity.VIGOROUS,
        duration_minutes=30,
        met_value=12.0,
        weight_kg_snapshot=80.0,
        estimated_burn_kcal=480.0,
    )

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.users.find_by_id = AsyncMock(return_value=user)
    mock_uow.workouts.save = AsyncMock(return_value=saved_log)
    mock_uow.commit = AsyncMock()

    cmd = LogWorkoutCommand(
        user_id=str(uuid.uuid4()),
        workout_type=WorkoutType.HIIT,
        intensity=Intensity.VIGOROUS,
        duration_minutes=30,
        logged_at=datetime.now(timezone.utc),
    )

    with patch(
        "src.app.handlers.command_handlers.log_workout_command_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ):
        result = await handler.handle(cmd)

    assert result["estimated_burn_kcal"] == 480.0
