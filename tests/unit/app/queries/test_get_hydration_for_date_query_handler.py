"""Unit tests for GetHydrationForDateQueryHandler."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.app.handlers.query_handlers.get_hydration_for_date_query_handler import (
    GetHydrationForDateQueryHandler,
)
from src.app.queries.hydration.get_hydration_for_date_query import (
    GetHydrationForDateQuery,
)
from src.domain.model.hydration.hydration_entry import DrinkType, HydrationEntry


def _make_entry(user_id: str, volume_ml: int = 500, drink_type=DrinkType.WATER):
    return HydrationEntry(
        hydration_entry_id=str(uuid.uuid4()),
        user_id=user_id,
        drink_type=drink_type,
        volume_ml=volume_ml,
        logged_at=datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def handler():
    return GetHydrationForDateQueryHandler()


def _mock_uow(entries, goal_ml=2000):
    mock_uow = AsyncMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=False)
    mock_uow.hydration.find_for_user_date = AsyncMock(return_value=entries)
    mock_uow.hydration.get_user_hydration_goal = AsyncMock(return_value=goal_ml)
    return mock_uow


@pytest.mark.asyncio
async def test_get_hydration_returns_entries_goal_and_total(handler):
    """Returns entries, goal_ml, and summed total_ml."""
    user_id = str(uuid.uuid4())
    entries = [_make_entry(user_id, 500), _make_entry(user_id, 250)]
    mock_uow = _mock_uow(entries, goal_ml=2000)

    with patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.resolve_user_timezone_async",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await handler.handle(
            GetHydrationForDateQuery(user_id=user_id, target_date=date(2026, 5, 18))
        )

    assert result["date"] == "2026-05-18"
    assert result["goal_ml"] == 2000
    assert result["total_ml"] == 750
    assert len(result["entries"]) == 2


@pytest.mark.asyncio
async def test_get_hydration_empty_day(handler):
    """Empty day returns zero total_ml and empty entries."""
    user_id = str(uuid.uuid4())
    mock_uow = _mock_uow([], goal_ml=3000)

    with patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.resolve_user_timezone_async",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await handler.handle(
            GetHydrationForDateQuery(user_id=user_id, target_date=date(2026, 5, 18))
        )

    assert result["total_ml"] == 0
    assert result["goal_ml"] == 3000
    assert result["entries"] == []


@pytest.mark.asyncio
async def test_get_hydration_custom_goal_returned(handler):
    """Custom goal_ml from user record is returned accurately."""
    user_id = str(uuid.uuid4())
    mock_uow = _mock_uow([_make_entry(user_id, 500)], goal_ml=2500)

    with patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.resolve_user_timezone_async",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await handler.handle(
            GetHydrationForDateQuery(user_id=user_id, target_date=date(2026, 5, 18))
        )

    assert result["goal_ml"] == 2500


@pytest.mark.asyncio
async def test_get_hydration_entry_shape(handler):
    """Each entry contains the required fields."""
    user_id = str(uuid.uuid4())
    entry = _make_entry(user_id, 250, DrinkType.BLACK_COFFEE)
    mock_uow = _mock_uow([entry])

    with patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.AsyncUnitOfWork",
        return_value=mock_uow,
    ), patch(
        "src.app.handlers.query_handlers.get_hydration_for_date_query_handler.resolve_user_timezone_async",
        new=AsyncMock(return_value="UTC"),
    ):
        result = await handler.handle(
            GetHydrationForDateQuery(user_id=user_id, target_date=date(2026, 5, 18))
        )

    e = result["entries"][0]
    assert "id" in e
    assert e["drink_type"] == "BLACK_COFFEE"
    assert e["volume_ml"] == 250
    assert "logged_at" in e
