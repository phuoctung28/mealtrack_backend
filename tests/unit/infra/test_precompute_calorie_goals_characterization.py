"""Characterization gate for DailyContextPrecomputeService._precompute_db.

Locks the CURRENT per-user `calorie_goals` output of `_precompute_db` for a
mixed batch (custom-macro fallback, weekly-budget-adjusted, stale-revision
skip, missing-profile skip) before Wave 2 item 15 batches this N+1 loop.

Uses fakes for the AsyncUnitOfWork session (raw SQL boundary) instead of a
real Postgres-only integration DB, since `_precompute_db` relies on
Postgres-specific `ANY(:ids)` array binding and `pg_insert(...).on_conflict_do_nothing`
that SQLite (the default unit-test engine) cannot execute.
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.services.weekly_budget_service import AdjustedDailyTargets
from src.infra.services.daily_context_precompute_service import (
    DailyContextPrecomputeService,
)

TODAY = date(2026, 4, 22)  # Wednesday
TZ_NAME = "Asia/Ho_Chi_Minh"


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeSession:
    """Replays canned rows for the sequential SELECTs in `_precompute_db`."""

    def __init__(self, query_results):
        self._results = list(query_results)
        self.executed_count = 0

    async def execute(self, _stmt, _params=None):
        self.executed_count += 1
        if not self._results:
            return _FakeResult([])
        return self._results.pop(0)

    async def flush(self):
        pass


class _FakeUow:
    def __init__(self, session, weekly_budgets_by_user):
        self.session = session
        self._weekly_budgets_by_user = weekly_budgets_by_user
        self.weekly_budgets = SimpleNamespace(
            find_by_user_and_week=AsyncMock(side_effect=self._find_budget)
        )

    async def _find_budget(self, user_id, _week_start):
        return self._weekly_budgets_by_user.get(user_id)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


def _profile_row(
    user_id: str,
    *,
    profile_target_revision: int,
    custom_protein_g=None,
    custom_carbs_g=None,
    custom_fat_g=None,
):
    return SimpleNamespace(
        user_id=user_id,
        age=30,
        gender="male",
        height_cm=175,
        weight_kg=70,
        body_fat_percentage=None,
        job_type="desk",
        training_days_per_week=3,
        training_minutes_per_session=45,
        fitness_goal="maintain",
        training_level="beginner",
        dietary_preferences=[],
        custom_protein_g=custom_protein_g,
        custom_carbs_g=custom_carbs_g,
        custom_fat_g=custom_fat_g,
        profile_target_revision=profile_target_revision,
        language_code="en",
    )


def _pref_row(user_id: str):
    return SimpleNamespace(
        user_id=user_id,
        meal_reminders_enabled=False,
        daily_summary_enabled=False,
        hydration_reminders_enabled=False,
        breakfast_time_minutes=None,
        lunch_time_minutes=None,
        dinner_time_minutes=None,
        daily_summary_time_minutes=None,
        language="en",
    )


@pytest.fixture(autouse=True)
def clear_sentinel():
    from src.infra.services import daily_context_precompute_service as module

    module._precomputed_today.clear()
    yield
    module._precomputed_today.clear()


@pytest.mark.asyncio
async def test_precompute_db_locks_calorie_goals_for_mixed_user_batch():
    """Locks calorie_goals dict for: custom-macro fallback, weekly-budget path,
    stale target_revision (skipped), and missing profile (skipped).

    Also locks the CURRENT return-value semantics: `_precompute_db` returns the
    count of pref rows fetched, NOT the count of users who received a goal.
    """
    user_custom = "user-custom-macros"
    user_budget_ok = "user-budget-ok"
    user_budget_stale = "user-budget-stale"
    user_no_profile = "user-no-profile"

    pref_rows = [
        _pref_row(user_custom),
        _pref_row(user_budget_ok),
        _pref_row(user_budget_stale),
        _pref_row(user_no_profile),
    ]
    token_rows = [
        SimpleNamespace(user_id=user_custom, fcm_token="tok-1"),
        SimpleNamespace(user_id=user_budget_ok, fcm_token="tok-2"),
        SimpleNamespace(user_id=user_budget_stale, fcm_token="tok-3"),
        SimpleNamespace(user_id=user_no_profile, fcm_token="tok-4"),
    ]
    profile_rows = [
        _profile_row(
            user_custom,
            profile_target_revision=1,
            custom_protein_g=100,
            custom_carbs_g=200,
            custom_fat_g=50,
        ),
        _profile_row(user_budget_ok, profile_target_revision=5),
        _profile_row(user_budget_stale, profile_target_revision=2),
        # user_no_profile intentionally omitted — simulates missing current profile
    ]
    consumed_rows: list = []

    weekly_budget_ok = SimpleNamespace(
        weekly_budget_id="wb-ok",
        user_id=user_budget_ok,
        week_start_date=TODAY - timedelta(days=TODAY.weekday()),
        target_revision=5,
        target_calories=14000.0,
        target_protein=1050.0,
        target_carbs=1400.0,
        target_fat=490.0,
        consumed_calories=0.0,
        consumed_protein=0.0,
        consumed_carbs=0.0,
        consumed_fat=0.0,
    )
    weekly_budget_stale = SimpleNamespace(
        weekly_budget_id="wb-stale",
        user_id=user_budget_stale,
        week_start_date=TODAY - timedelta(days=TODAY.weekday()),
        target_revision=1,  # mismatches profile's profile_target_revision=2
        target_calories=14000.0,
        target_protein=1050.0,
        target_carbs=1400.0,
        target_fat=490.0,
        consumed_calories=0.0,
        consumed_protein=0.0,
        consumed_carbs=0.0,
        consumed_fat=0.0,
    )
    session = _FakeSession(
        [
            _FakeResult(pref_rows),
            _FakeResult(token_rows),
            _FakeResult(profile_rows),
            _FakeResult(consumed_rows),
            _FakeResult([weekly_budget_ok, weekly_budget_stale]),
            _FakeResult([]),  # batch cheat days
            _FakeResult([]),  # batch READY meals
            _FakeResult([]),  # batch hydratable meal dates
            _FakeResult([]),  # batch movement by local date
        ]
    )
    fake_uow = _FakeUow(session, {})

    svc = DailyContextPrecomputeService()

    async def _fake_effective(*, user_id, cheat_dates=None, weekly_preload=None, **_kwargs):
        assert user_id == user_budget_ok, "only the matching-revision user should reach here"
        assert cheat_dates == []
        assert weekly_preload is not None
        return SimpleNamespace(
            adjusted=AdjustedDailyTargets(
                calories=1900.0,
                protein=140.0,
                carbs=180.0,
                fat=60.0,
                bmr_floor_active=False,
                remaining_days=5,
            )
        )

    captured_build_args: dict = {}

    def _fake_build_notification_rows(**kwargs):
        captured_build_args.update(kwargs)
        return []

    with (
        patch(
            "src.infra.services.daily_context_precompute_service.AsyncUnitOfWork",
            lambda: fake_uow,
        ),
        patch(
            "src.infra.services.daily_context_precompute_service.WeeklyBudgetService.get_effective_adjusted_daily_async",
            new_callable=AsyncMock,
            side_effect=_fake_effective,
        ),
        patch.object(
            svc,
            "_build_notification_rows",
            side_effect=_fake_build_notification_rows,
        ),
    ):
        processed_count = await svc._precompute_db(TZ_NAME, TODAY)

    # Custom-macro fallback: round(100*4 + 200*4 + 50*9) = round(400+800+450)
    # Weekly-budget path: policy-unchanged adjusted.calories (STANDARD preset, not custom)
    assert captured_build_args["calorie_goals"] == {
        user_custom: 1650,
        user_budget_ok: 1900,
    }
    assert user_budget_stale not in captured_build_args["calorie_goals"]
    assert user_no_profile not in captured_build_args["calorie_goals"]

    # CURRENT behavior: return value is len(pref_rows), regardless of per-user
    # skips (stale revision / missing profile). Not "count of users with a goal".
    assert processed_count == len(pref_rows) == 4


@pytest.mark.asyncio
async def test_precompute_db_returns_zero_when_no_eligible_users():
    """No pref rows (query 1 empty) → short-circuits to 0 without further queries."""
    session = _FakeSession([_FakeResult([])])
    fake_uow = _FakeUow(session, {})
    svc = DailyContextPrecomputeService()

    with patch(
        "src.infra.services.daily_context_precompute_service.AsyncUnitOfWork",
        lambda: fake_uow,
    ):
        processed_count = await svc._precompute_db(TZ_NAME, TODAY)

    assert processed_count == 0
    assert session.executed_count == 1
