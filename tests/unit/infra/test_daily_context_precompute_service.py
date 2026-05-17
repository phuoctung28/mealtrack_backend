import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_skips_if_sentinel_exists():
    """Pre-compute is skipped when sentinel key already exists in Redis."""
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=True)
    svc = DailyContextPrecomputeService(redis_client=redis)

    with patch.object(svc, "_precompute_db_sync") as mock_sync:
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", date(2026, 4, 22))
        mock_sync.assert_not_called()


@pytest.mark.asyncio
async def test_runs_and_sets_sentinel_when_missing():
    """Pre-compute runs and sets sentinel when key is absent."""
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=False)
    redis.hset_batch = AsyncMock()
    redis.set = AsyncMock()
    svc = DailyContextPrecomputeService(redis_client=redis)

    with patch.object(svc, "_precompute_db_sync", return_value=[]) as mock_sync:
        await svc.precompute_for_timezone("Asia/Ho_Chi_Minh", date(2026, 4, 22))
        mock_sync.assert_called_once()
        redis.set.assert_called_once()


def test_sentinel_key_format():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    key = svc.sentinel_key(date(2026, 4, 22), "Asia/Ho_Chi_Minh")
    assert key == "precomputed:2026-04-22:Asia/Ho_Chi_Minh"


def test_context_key_format():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    assert svc.context_key("user-123") == "user_daily_context:user-123"


def test_user_calorie_goal_reads_weekly_macro_budget_table():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

    session = MagicMock()
    weekly_budget_row = MagicMock()
    weekly_budget_row.target_calories = 14000
    session.execute.return_value.fetchone.return_value = weekly_budget_row

    svc = DailyContextPrecomputeService(redis_client=MagicMock())
    result = svc._get_user_calorie_goal(session, "user-123", date(2026, 5, 17))

    executed_sql = str(session.execute.call_args.args[0])
    assert result == 2000
    assert "weekly_macro_budgets" in executed_sql
    assert "weekly_budgets" not in executed_sql
