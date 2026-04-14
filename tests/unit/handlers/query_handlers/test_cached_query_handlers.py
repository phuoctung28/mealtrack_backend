"""
Unit tests for cache hit/miss behaviour on query handlers that use Redis.
All tests use a mock CacheService — no real Redis required.
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.domain.cache.cache_keys import CacheKeys
from src.app.queries.tdee import GetUserTdeeQuery


class TestGetUserTdeeQueryHandlerCache:
    """Cache behaviour for GetUserTdeeQueryHandler."""

    @pytest.mark.asyncio
    async def test_returns_cached_value_on_hit(self):
        """On a Redis cache hit the DB is never touched."""
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler

        cached_payload = {"user_id": "u1", "tdee": 2000.0, "bmr": 1700.0}
        cache_service = MagicMock()
        cache_service.get_json = AsyncMock(return_value=cached_payload)
        cache_service.set_json = AsyncMock()

        handler = GetUserTdeeQueryHandler(cache_service=cache_service)
        query = GetUserTdeeQuery(user_id="u1")

        result = await handler.handle(query)

        assert result == cached_payload
        cache_service.get_json.assert_awaited_once()
        cache_service.set_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stores_result_in_cache_on_miss(self):
        """On a Redis cache miss the result is stored for next time."""
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler

        db_result = {"user_id": "u1", "tdee": 2000.0, "bmr": 1700.0, "macros": {}}
        cache_service = MagicMock()
        cache_service.get_json = AsyncMock(return_value=None)  # miss
        cache_service.set_json = AsyncMock()

        handler = GetUserTdeeQueryHandler(cache_service=cache_service)
        query = GetUserTdeeQuery(user_id="u1")

        with patch.object(handler, '_compute_tdee', AsyncMock(return_value=db_result)):
            result = await handler.handle(query)

        assert result == db_result
        cache_service.set_json.assert_awaited_once()
        # Verify the cache key used
        call_args = cache_service.set_json.call_args
        expected_key, _ = CacheKeys.user_tdee("u1")
        assert call_args[0][0] == expected_key

    @pytest.mark.asyncio
    async def test_works_without_cache_service(self):
        """Handler works normally when no cache_service provided."""
        from src.app.handlers.query_handlers.get_user_tdee_query_handler import GetUserTdeeQueryHandler

        db_result = {"user_id": "u1", "tdee": 2000.0}
        handler = GetUserTdeeQueryHandler()  # no cache_service
        query = GetUserTdeeQuery(user_id="u1")

        with patch.object(handler, '_compute_tdee', AsyncMock(return_value=db_result)):
            result = await handler.handle(query)

        assert result == db_result


class TestGetWeeklyBudgetQueryHandlerCache:
    """Cache behaviour for GetWeeklyBudgetQueryHandler."""

    @pytest.mark.asyncio
    async def test_returns_cached_value_on_hit(self):
        """On a Redis cache hit find_by_user_and_week is never called."""
        import zoneinfo
        from datetime import date
        from src.app.handlers.query_handlers.get_weekly_budget_query_handler import GetWeeklyBudgetQueryHandler
        from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery

        cached_payload = {"week_start_date": "2024-01-01", "target_calories": 14000.0}
        cache_service = MagicMock()
        cache_service.get_json = AsyncMock(return_value=cached_payload)
        cache_service.set_json = AsyncMock()

        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)

        handler = GetWeeklyBudgetQueryHandler(uow=mock_uow, cache_service=cache_service)
        query = GetWeeklyBudgetQuery(user_id="u1", target_date=date(2024, 1, 1), header_timezone="UTC")

        with patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler.resolve_user_timezone",
            return_value="UTC",
        ), patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler.get_zone_info",
            return_value=zoneinfo.ZoneInfo("UTC"),
        ), patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler.get_user_monday",
            return_value=date(2024, 1, 1),
        ):
            result = await handler.handle(query)

        assert result == cached_payload
        cache_service.get_json.assert_awaited_once()
        cache_service.set_json.assert_not_awaited()
        mock_uow.weekly_budgets.find_by_user_and_week.assert_not_called()

    @pytest.mark.asyncio
    async def test_stores_result_in_cache_on_miss(self):
        """On a Redis cache miss the result is stored with the correct key and TTL."""
        import zoneinfo
        from datetime import date
        from src.app.handlers.query_handlers.get_weekly_budget_query_handler import GetWeeklyBudgetQueryHandler
        from src.app.queries.get_weekly_budget_query import GetWeeklyBudgetQuery

        cache_service = MagicMock()
        cache_service.get_json = AsyncMock(return_value=None)  # miss
        cache_service.set_json = AsyncMock()

        mock_uow = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow.cheat_days.find_by_user_and_date_range.return_value = []

        week_start = date(2024, 1, 1)
        mock_budget = MagicMock(
            target_calories=14000.0, target_protein=490.0, target_carbs=1400.0, target_fat=490.0,
            consumed_calories=0.0, consumed_protein=0.0, consumed_carbs=0.0, consumed_fat=0.0,
            remaining_protein=490.0, remaining_carbs=1400.0, remaining_fat=490.0,
        )
        mock_uow.weekly_budgets.find_by_user_and_week.return_value = mock_budget

        mock_effective = MagicMock()
        mock_effective.adjusted = MagicMock(
            calories=2000.0, carbs=200.0, fat=70.0, protein=70.0,
            bmr_floor_active=False, remaining_days=1,
        )
        mock_effective.consumed_before_today = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        mock_effective.consumed_total = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        mock_effective.skipped_days = 0
        mock_effective.show_logging_prompt = False
        mock_effective.logged_past_days = 0

        handler = GetWeeklyBudgetQueryHandler(uow=mock_uow, cache_service=cache_service)
        query = GetWeeklyBudgetQuery(user_id="u1", target_date=date(2024, 1, 1), header_timezone="UTC")

        expected_key, expected_ttl = CacheKeys.weekly_budget("u1", week_start)

        with patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler.resolve_user_timezone",
            return_value="UTC",
        ), patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler.get_zone_info",
            return_value=zoneinfo.ZoneInfo("UTC"),
        ), patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler.get_user_monday",
            return_value=week_start,
        ), patch(
            "src.app.handlers.query_handlers.get_weekly_budget_query_handler.WeeklyBudgetService"
        ) as mock_svc, patch.object(
            handler, "_sync_targets_if_stale", AsyncMock(return_value=(mock_budget, 1800.0))
        ):
            mock_svc.get_effective_adjusted_daily.return_value = mock_effective
            result = await handler.handle(query)

        cache_service.set_json.assert_awaited_once()
        call_args = cache_service.set_json.call_args[0]
        assert call_args[0] == expected_key
        assert call_args[2] == expected_ttl

    @pytest.mark.asyncio
    async def test_passes_cache_service_to_tdee_handler(self):
        """_create_weekly_budget passes cache_service to GetUserTdeeQueryHandler."""
        from datetime import date
        from src.app.handlers.query_handlers.get_weekly_budget_query_handler import GetWeeklyBudgetQueryHandler

        cache_service = MagicMock()
        mock_uow = MagicMock()
        mock_uow.users.get_profile.return_value = MagicMock(fitness_goal="cut")
        mock_uow.weekly_budgets.create = MagicMock()

        handler = GetWeeklyBudgetQueryHandler(uow=mock_uow, cache_service=cache_service)

        tdee_instance = MagicMock()
        tdee_instance.handle = AsyncMock(return_value={
            "target_calories": 2000,
            "macros": {"protein": 70, "carbs": 200, "fat": 70},
            "bmr": 1800,
        })

        with patch(
            "src.app.handlers.query_handlers.get_user_tdee_query_handler.GetUserTdeeQueryHandler",
            return_value=tdee_instance,
        ) as MockTdeeClass:
            await handler._create_weekly_budget(mock_uow, "u1", date(2024, 1, 1), date(2024, 1, 1))

        MockTdeeClass.assert_called_once_with(cache_service=cache_service)
