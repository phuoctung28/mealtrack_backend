"""Tests that get_daily_macros handler opens UnitOfWork once on cache miss."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app.handlers.query_handlers.get_daily_macros_query_handler import (
    GetDailyMacrosQueryHandler,
)
from src.app.queries.meal import GetDailyMacrosQuery


def _make_handler():
    cache = MagicMock()
    cache.get_json = AsyncMock(return_value=None)  # cache miss
    cache.set_json = AsyncMock()
    return GetDailyMacrosQueryHandler(cache_service=cache)


@pytest.mark.asyncio
async def test_cache_miss_opens_uow_once():
    """On a cache miss, UnitOfWork is instantiated exactly once for DB reads."""
    handler = _make_handler()
    query = GetDailyMacrosQuery(user_id="u1", target_date=date(2026, 4, 18))

    with patch(
        "src.app.handlers.query_handlers.get_daily_macros_query_handler.UnitOfWork"
    ) as mock_cls:
        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        fake_user = MagicMock()
        fake_user.timezone = "UTC"
        mock_uow.users.find_by_id.return_value = fake_user
        mock_uow.meals.find_by_date.return_value = []
        mock_uow.weekly_budgets.find_by_user_and_week.return_value = None
        mock_cls.return_value = mock_uow

        # Patch TDEE handler so it doesn't open its own UoW
        with patch(
            "src.app.handlers.query_handlers.get_user_tdee_query_handler.GetUserTdeeQueryHandler"
        ) as mock_tdee_cls:
            mock_tdee = MagicMock()
            mock_tdee.handle = AsyncMock(return_value={"target_calories": 2000, "macros": {}, "bmr": 1800})
            mock_tdee_cls.return_value = mock_tdee
            await handler.handle(query)

    assert mock_cls.call_count == 1, (
        f"Expected 1 UoW open on cache miss, got {mock_cls.call_count}"
    )


@pytest.mark.asyncio
async def test_weekly_budget_fetched_in_shared_uow():
    """weekly_budgets.find_by_user_and_week is called on the same UoW as find_by_date."""
    handler = _make_handler()
    query = GetDailyMacrosQuery(user_id="u1", target_date=date(2026, 4, 18))
    uow_instances = []

    class TrackingUow:
        def __init__(self):
            self.users = MagicMock()
            fake_user = MagicMock()
            fake_user.timezone = "UTC"
            self.users.find_by_id.return_value = fake_user
            self.meals = MagicMock()
            self.meals.find_by_date.return_value = []
            self.weekly_budgets = MagicMock()
            self.weekly_budgets.find_by_user_and_week.return_value = None
            uow_instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch(
        "src.app.handlers.query_handlers.get_daily_macros_query_handler.UnitOfWork",
        TrackingUow,
    ):
        with patch(
            "src.app.handlers.query_handlers.get_user_tdee_query_handler.GetUserTdeeQueryHandler"
        ) as mock_tdee_cls:
            mock_tdee = MagicMock()
            mock_tdee.handle = AsyncMock(return_value={"target_calories": 2000, "macros": {}, "bmr": 1800})
            mock_tdee_cls.return_value = mock_tdee
            await handler.handle(query)

    first_uow = uow_instances[0]
    first_uow.meals.find_by_date.assert_called_once()
    first_uow.weekly_budgets.find_by_user_and_week.assert_called_once()
