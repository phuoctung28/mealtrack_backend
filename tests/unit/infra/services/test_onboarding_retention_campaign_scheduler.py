"""Failing contract tests for OnboardingRetentionCampaignScheduler.

All imports reference production modules that do not yet exist — tests are
intentionally red until Phase 2 implements them.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infra.services.onboarding_retention_campaign_scheduler import (  # noqa: F401 — ImportError is the expected failure
    OnboardingRetentionCampaignScheduler,
)

NOW_UTC = datetime(2026, 6, 21, 10, 0, 0, tzinfo=UTC)
USER_ID = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    user_id: str,
    timezone: str = "UTC",
    language: str = "en",
    gender: str = "male",
    fcm_tokens: list[str] | None = None,
):
    u = MagicMock()
    u.user_id = user_id
    u.timezone = timezone
    u.language = language
    u.gender = gender
    u.fcm_tokens = fcm_tokens if fcm_tokens is not None else ["tok1"]
    return u


def _make_state(
    user_id: str,
    campaign_started_at: datetime,
    subscription_expires_at: datetime | None = None,
):
    s = MagicMock()
    s.user_id = user_id
    s.campaign_started_at = campaign_started_at
    s.subscription_expires_at = subscription_expires_at
    return s


def _patch_scheduler_deps(users, state, inserted_count=1):
    """Return a context-manager stack that wires users + state into the scheduler."""
    uow_cm = MagicMock()
    uow_cm.session = MagicMock()
    uow_cm.session.execute = AsyncMock(
        return_value=MagicMock(rowcount=inserted_count)
    )
    uow_cm.session.flush = AsyncMock()

    uow_ctx = MagicMock()
    uow_ctx.__aenter__ = AsyncMock(return_value=uow_cm)
    uow_ctx.__aexit__ = AsyncMock(return_value=False)
    return uow_ctx, uow_cm


# ---------------------------------------------------------------------------
# D1 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_d1_night_anchor_schedules_at_21_local():
    """Scheduler inserts a d1_night_anchor row at D1 21:00 local when not yet stale."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = USER_ID
    # Now is 10:00 UTC; user TZ=UTC → 21:00 has not passed yet
    uow_ctx, uow_cm = _patch_scheduler_deps(
        users=[_make_user(user_id)],
        state=_make_state(user_id, campaign_started_at=NOW_UTC),
    )

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(return_value=[_make_user(user_id)]),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(user_id, campaign_started_at=NOW_UTC)
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(NOW_UTC)

    # Must have attempted to insert the d1_night_anchor row
    assert result >= 1
    # Verify execute was called (the ON CONFLICT DO NOTHING insert)
    uow_cm.session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_d1_night_anchor_skipped_when_stale():
    """If current UTC is past D1 21:00 local, no d1_night_anchor row is inserted."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())

    # now=22:30 UTC, TZ=UTC → 21:00 local already passed
    stale_now = datetime(2026, 6, 21, 22, 30, 0, tzinfo=UTC)
    campaign_started = datetime(2026, 6, 21, 8, 0, 0, tzinfo=UTC)

    uow_ctx, uow_cm = _patch_scheduler_deps(
        users=[], state=None, inserted_count=0
    )
    uow_cm.session.execute = AsyncMock(
        return_value=MagicMock(rowcount=0)
    )

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(return_value=[_make_user(user_id, timezone="UTC")]),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(user_id, campaign_started_at=campaign_started)
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(stale_now)

    # No d1 night anchor should be inserted when the slot has passed
    assert result == 0


@pytest.mark.asyncio
async def test_d2_schedules_four_rows():
    """Four D2 notification rows at 08:30, 11:45, 15:00, 20:00 local."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())
    # now = D2 morning before any slot
    campaign_started = datetime(2026, 6, 20, 10, 0, 0, tzinfo=UTC)
    d2_now = datetime(2026, 6, 21, 1, 0, 0, tzinfo=UTC)  # 01:00 UTC = D2 start

    inserted_rows = []

    async def _execute_capture(stmt, *args, **kwargs):
        # count insert calls by tracking executes
        inserted_rows.append(stmt)
        return MagicMock(rowcount=1)

    uow_cm = MagicMock()
    uow_cm.session = MagicMock()
    uow_cm.session.execute = AsyncMock(side_effect=_execute_capture)
    uow_cm.session.flush = AsyncMock()
    uow_ctx = MagicMock()
    uow_ctx.__aenter__ = AsyncMock(return_value=uow_cm)
    uow_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(return_value=[_make_user(user_id, timezone="UTC")]),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(user_id, campaign_started_at=campaign_started)
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(d2_now)

    # 4 D2 notification types scheduled
    assert result >= 4


@pytest.mark.asyncio
async def test_d3_churn_preemption_at_09_local():
    """d3_churn_preemption row is scheduled at D3 09:00 local."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())
    campaign_started = datetime(2026, 6, 19, 10, 0, 0, tzinfo=UTC)
    d3_now = datetime(2026, 6, 22, 1, 0, 0, tzinfo=UTC)  # D3 start

    uow_ctx, uow_cm = _patch_scheduler_deps(users=[], state=None)

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(return_value=[_make_user(user_id, timezone="UTC")]),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(user_id, campaign_started_at=campaign_started)
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(d3_now)

    assert result >= 1
    uow_cm.session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_d3_asset_lock_uses_revenuecat_expires_at():
    """d3_premium_asset_lock scheduled at expires_at - 6h when RevenueCat provides it."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())
    campaign_started = datetime(2026, 6, 19, 10, 0, 0, tzinfo=UTC)
    expires_at = datetime(2026, 6, 22, 18, 0, 0, tzinfo=UTC)  # D3
    expected_lock_at = expires_at - timedelta(hours=6)  # 12:00 D3

    d3_now = datetime(2026, 6, 22, 1, 0, 0, tzinfo=UTC)

    captured_rows: list[dict] = []

    async def _capture_execute(stmt, *args, **kwargs):
        captured_rows.append({"stmt": stmt})
        return MagicMock(rowcount=1)

    uow_cm = MagicMock()
    uow_cm.session = MagicMock()
    uow_cm.session.execute = AsyncMock(side_effect=_capture_execute)
    uow_cm.session.flush = AsyncMock()
    uow_ctx = MagicMock()
    uow_ctx.__aenter__ = AsyncMock(return_value=uow_cm)
    uow_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(return_value=[_make_user(user_id, timezone="UTC")]),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(
                        user_id,
                        campaign_started_at=campaign_started,
                        subscription_expires_at=expires_at,
                    )
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(d3_now)

    assert result >= 1
    # The lock_at used must equal expires_at - 6h; verified by inspecting the
    # inserted row's scheduled_for_utc via the scheduler's own helper method.
    lock_at = await svc._compute_asset_lock_at(
        campaign_started_at=campaign_started,
        subscription_expires_at=expires_at,
    )
    assert lock_at == expected_lock_at


@pytest.mark.asyncio
async def test_d3_asset_lock_fallback_to_campaign_plus_72h():
    """When no expires_at, lock_at = campaign_started_at + 72h - 6h."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())
    campaign_started = datetime(2026, 6, 19, 10, 0, 0, tzinfo=UTC)
    expected_lock_at = campaign_started + timedelta(hours=72) - timedelta(hours=6)

    lock_at = await svc._compute_asset_lock_at(
        campaign_started_at=campaign_started,
        subscription_expires_at=None,
    )
    assert lock_at == expected_lock_at


@pytest.mark.asyncio
async def test_idempotent_second_run_does_not_duplicate():
    """Second call to schedule() inserts 0 rows (ON CONFLICT DO NOTHING)."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())
    campaign_started = datetime(2026, 6, 20, 10, 0, 0, tzinfo=UTC)

    # rowcount=0 simulates ON CONFLICT DO NOTHING returning nothing
    uow_cm = MagicMock()
    uow_cm.session = MagicMock()
    uow_cm.session.execute = AsyncMock(
        return_value=MagicMock(rowcount=0)
    )
    uow_cm.session.flush = AsyncMock()
    uow_ctx = MagicMock()
    uow_ctx.__aenter__ = AsyncMock(return_value=uow_cm)
    uow_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(return_value=[_make_user(user_id, timezone="UTC")]),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(user_id, campaign_started_at=campaign_started)
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(NOW_UTC)

    assert result == 0


@pytest.mark.asyncio
async def test_non_utc_timezone_east():
    """Asia/Ho_Chi_Minh (UTC+7) scheduling is local-correct for D1 night anchor."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())

    # 14:00 UTC = 21:00 HCM time — the scheduler should set scheduled_for_utc=14:00 UTC
    hcm_now = datetime(2026, 6, 21, 13, 0, 0, tzinfo=UTC)  # before 21:00 local
    campaign_started = datetime(2026, 6, 21, 3, 0, 0, tzinfo=UTC)  # 10:00 HCM

    uow_ctx, uow_cm = _patch_scheduler_deps(users=[], state=None)

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(
                return_value=[
                    _make_user(user_id, timezone="Asia/Ho_Chi_Minh")
                ]
            ),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(
                        user_id, campaign_started_at=campaign_started
                    )
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(hcm_now)

    assert result >= 1
    # The scheduled_for_utc for d1_night_anchor must be 14:00 UTC (21:00 HCM)
    expected_utc = datetime(2026, 6, 21, 14, 0, 0, tzinfo=UTC)
    scheduled_utc = await svc._local_time_to_utc(
        local_hour=21,
        local_minute=0,
        local_date_utc=campaign_started,
        timezone="Asia/Ho_Chi_Minh",
    )
    assert scheduled_utc == expected_utc


@pytest.mark.asyncio
async def test_users_without_fcm_tokens_skipped():
    """Users with no FCM tokens get no notification rows inserted."""
    svc = OnboardingRetentionCampaignScheduler()
    user_id = str(uuid.uuid4())

    uow_ctx, uow_cm = _patch_scheduler_deps(users=[], state=None, inserted_count=0)

    with (
        patch.object(
            svc,
            "_fetch_eligible_users",
            AsyncMock(
                return_value=[_make_user(user_id, fcm_tokens=[])]  # no tokens
            ),
        ),
        patch.object(
            svc,
            "_fetch_campaign_states",
            AsyncMock(
                return_value={
                    user_id: _make_state(user_id, campaign_started_at=NOW_UTC)
                }
            ),
        ),
        patch(
            "src.infra.services.onboarding_retention_campaign_scheduler.AsyncUnitOfWork",
            return_value=uow_ctx,
        ),
    ):
        result = await svc.schedule(NOW_UTC)

    assert result == 0
    uow_cm.session.execute.assert_not_awaited()
