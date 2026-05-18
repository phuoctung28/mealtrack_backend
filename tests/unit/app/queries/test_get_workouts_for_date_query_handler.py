"""Unit tests for GetWorkoutsForDateQueryHandler."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.app.handlers.query_handlers.get_workouts_for_date_query_handler import (
    GetWorkoutsForDateQueryHandler,
)
from src.app.queries.workout.get_workouts_for_date_query import GetWorkoutsForDateQuery
from src.domain.model.workout.workout_log import Intensity, WorkoutLog, WorkoutType


def _make_log(user_id: str, burn: float | None = 300.0) -> WorkoutLog:
    return WorkoutLog(
        workout_log_id=str(uuid.uuid4()),
        user_id=user_id,
        workout_type=WorkoutType.RUNNING,
        intensity=Intensity.MODERATE,
        duration_minutes=45,
        logged_at=datetime(2026, 5, 18, 7, 30, tzinfo=timezone.utc),
        met_value=8.3,
        weight_kg_snapshot=75.0 if burn else None,
        estimated_burn_kcal=burn,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def handler():
    return GetWorkoutsForDateQueryHandler()


@pytest.mark.asyncio
async def test_get_workouts_returns_entries_and_total(handler):
    """Returns entries list and summed total_burn_kcal."""
    user_id = str(uuid.uuid4())
    log1 = _make_log(user_id, burn=300.0)
    log2 = _make_log(user_id, burn=200.0)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.workouts.find_for_user_date = AsyncMock(return_value=[log1, log2])

    with patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.resolve_user_timezone_async",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await handler.handle(
            GetWorkoutsForDateQuery(
                user_id=user_id, target_date=date(2026, 5, 18)
            )
        )

    assert result["date"] == "2026-05-18"
    assert len(result["entries"]) == 2
    assert result["total_burn_kcal"] == 500.0


@pytest.mark.asyncio
async def test_get_workouts_empty_day_returns_null_total(handler):
    """Empty day returns empty entries and None total_burn_kcal."""
    user_id = str(uuid.uuid4())

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.workouts.find_for_user_date = AsyncMock(return_value=[])

    with patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.resolve_user_timezone_async",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await handler.handle(
            GetWorkoutsForDateQuery(
                user_id=user_id, target_date=date(2026, 5, 18)
            )
        )

    assert result["entries"] == []
    assert result["total_burn_kcal"] is None


@pytest.mark.asyncio
async def test_get_workouts_null_burn_excluded_from_total(handler):
    """Entries with null burn are excluded from total; total is None when all null."""
    user_id = str(uuid.uuid4())
    log_no_burn = _make_log(user_id, burn=None)

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.workouts.find_for_user_date = AsyncMock(return_value=[log_no_burn])

    with patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.resolve_user_timezone_async",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await handler.handle(
            GetWorkoutsForDateQuery(
                user_id=user_id, target_date=date(2026, 5, 18)
            )
        )

    assert len(result["entries"]) == 1
    assert result["total_burn_kcal"] is None


@pytest.mark.asyncio
async def test_get_workouts_uses_header_timezone(handler):
    """Timezone header is forwarded to resolve_user_timezone_async."""
    user_id = str(uuid.uuid4())

    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.workouts.find_for_user_date = AsyncMock(return_value=[])

    mock_resolve = AsyncMock(return_value="Asia/Ho_Chi_Minh")

    with patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_workouts_for_date_query_handler.resolve_user_timezone_async",
        new=mock_resolve,
    ):
        await handler.handle(
            GetWorkoutsForDateQuery(
                user_id=user_id,
                target_date=date(2026, 5, 18),
                header_timezone="Asia/Ho_Chi_Minh",
            )
        )

    mock_resolve.assert_called_once_with(
        user_id, mock_uow, header_timezone="Asia/Ho_Chi_Minh"
    )
