"""Unit tests for CronTrialPushService."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infra.services.cron_trial_push_service import (
    CronTrialPushService,
)

NOW_UTC = datetime(2026, 5, 17, 5, 0, 0, tzinfo=UTC)


def _make_sub(user_id: str, expires_at: datetime, status: str = "active"):
    sub = MagicMock()
    sub.user_id = user_id
    sub.status = status
    sub.expires_at = expires_at
    return sub


def _patch_uow_with_subs(subs):
    """Build an async context-manager mock wired to return `subs`."""
    uow_cm = MagicMock()
    uow_cm.subscriptions.find_expiring_in_window = AsyncMock(return_value=subs)
    uow_cm.session = MagicMock()
    uow_cm.session.execute = AsyncMock(return_value=MagicMock(rowcount=len(subs)))
    uow_cm.session.flush = AsyncMock()

    uow_ctx = MagicMock()
    uow_ctx.__aenter__ = AsyncMock(return_value=uow_cm)
    uow_ctx.__aexit__ = AsyncMock(return_value=False)
    return uow_ctx, uow_cm


@pytest.mark.asyncio
async def test_schedules_row_for_active_expiring_sub_with_token():
    svc = CronTrialPushService()
    user_id = str(uuid.uuid4())
    sub = _make_sub(user_id, NOW_UTC + timedelta(hours=6))

    uow_ctx, _uow = _patch_uow_with_subs([sub])

    with patch(
        "src.infra.services.cron_trial_push_service.AsyncUnitOfWork",
        return_value=uow_ctx,
    ), patch.object(
        CronTrialPushService,
        "_fetch_prefs",
        AsyncMock(return_value={
            user_id: {
                "language": "en",
                "timezone": "Asia/Ho_Chi_Minh",
                "gender": "male",
            }
        }),
    ), patch.object(
        CronTrialPushService,
        "_fetch_fcm_tokens",
        AsyncMock(return_value={user_id: ["tok1", "tok2"]}),
    ):
        n = await svc.check_and_schedule_pushes(NOW_UTC)
        assert n >= 1


@pytest.mark.asyncio
async def test_skips_user_without_fcm_token():
    svc = CronTrialPushService()
    user_id = str(uuid.uuid4())
    sub = _make_sub(user_id, NOW_UTC + timedelta(hours=6))

    uow_ctx, _uow = _patch_uow_with_subs([sub])

    with patch(
        "src.infra.services.cron_trial_push_service.AsyncUnitOfWork",
        return_value=uow_ctx,
    ), patch.object(
        CronTrialPushService,
        "_fetch_prefs",
        AsyncMock(return_value={
            user_id: {
                "language": "en",
                "timezone": "UTC",
                "gender": "male",
            }
        }),
    ), patch.object(
        CronTrialPushService,
        "_fetch_fcm_tokens",
        AsyncMock(return_value={}),  # no tokens
    ):
        n = await svc.check_and_schedule_pushes(NOW_UTC)
        assert n == 0


@pytest.mark.asyncio
async def test_returns_zero_when_no_subs_in_window():
    svc = CronTrialPushService()
    uow_ctx, _uow = _patch_uow_with_subs([])
    with patch(
        "src.infra.services.cron_trial_push_service.AsyncUnitOfWork",
        return_value=uow_ctx,
    ):
        assert await svc.check_and_schedule_pushes(NOW_UTC) == 0


@pytest.mark.asyncio
async def test_runs_single_schedule_pass():
    """One scheduling pass per run (no separate T-2d / T-1d windows)."""
    svc = CronTrialPushService()
    with patch.object(svc, "_schedule_due_pushes", AsyncMock(return_value=0)) as sd:
        await svc.check_and_schedule_pushes(NOW_UTC)
        sd.assert_awaited_once_with(NOW_UTC)


@pytest.mark.asyncio
async def test_queries_next_day_charge_window():
    """Subs charging within the next day are considered (from_days=0, to_days=1)."""
    svc = CronTrialPushService()
    uow_ctx, uow = _patch_uow_with_subs([])
    with patch(
        "src.infra.services.cron_trial_push_service.AsyncUnitOfWork",
        return_value=uow_ctx,
    ):
        await svc.check_and_schedule_pushes(NOW_UTC)
    uow.subscriptions.find_expiring_in_window.assert_awaited_once_with(
        from_days=0, to_days=1, now=NOW_UTC
    )


@pytest.mark.asyncio
async def test_language_resolution_falls_back_to_users_language_code():
    """pref.language=None + users.language_code='vi' → 'vi' (not 'en')."""
    session = MagicMock()
    row = MagicMock()
    row.user_id = "u1"
    row.language = None
    row.timezone = "Asia/Ho_Chi_Minh"
    row.gender = "female"
    row.language_code = "vi"
    session.execute = AsyncMock(return_value=MagicMock(fetchall=MagicMock(return_value=[row])))

    out = await CronTrialPushService._fetch_prefs(session, ["u1"])
    assert out["u1"]["language"] == "vi"


@pytest.mark.asyncio
async def test_language_resolution_pref_overrides_user():
    session = MagicMock()
    row = MagicMock()
    row.user_id = "u1"
    row.language = "en"
    row.timezone = "UTC"
    row.gender = "male"
    row.language_code = "vi"
    session.execute = AsyncMock(return_value=MagicMock(fetchall=MagicMock(return_value=[row])))

    out = await CronTrialPushService._fetch_prefs(session, ["u1"])
    assert out["u1"]["language"] == "en"


@pytest.mark.asyncio
async def test_language_resolution_unknown_falls_back_to_en():
    session = MagicMock()
    row = MagicMock()
    row.user_id = "u1"
    row.language = "fr"
    row.timezone = "UTC"
    row.gender = "male"
    row.language_code = "de"
    session.execute = AsyncMock(return_value=MagicMock(fetchall=MagicMock(return_value=[row])))

    out = await CronTrialPushService._fetch_prefs(session, ["u1"])
    assert out["u1"]["language"] == "en"


def test_build_row_schedules_two_hours_before_charge():
    svc = CronTrialPushService()
    pref = {
        "language": "vi",
        "timezone": "Asia/Ho_Chi_Minh",
        "gender": "female",
    }
    charge_at = NOW_UTC + timedelta(hours=10)
    row = svc._build_row(
        user_id="u1",
        charge_at=charge_at,
        tokens=["tok1"],
        pref=pref,
        now=NOW_UTC,
    )
    assert row is not None
    assert row["notification_type"] == "trial_expiry_1d"
    assert row["scheduled_for_utc"] == charge_at - timedelta(hours=2)
    assert row["status"] == "pending"
    assert row["context"]["language_code"] == "vi"
    assert row["context"]["gender"] == "female"
    assert row["context"]["fcm_tokens"] == ["tok1"]
    assert row["expires_at"] == row["scheduled_for_utc"] + timedelta(days=2)


def test_build_row_clamps_to_now_when_inside_lead_window():
    """Sub surfaced within the 2h lead → send now (still before charge), not skipped."""
    svc = CronTrialPushService()
    pref = {"language": "en", "timezone": "UTC", "gender": "male"}
    charge_at = NOW_UTC + timedelta(minutes=30)  # < 2h lead
    row = svc._build_row(
        user_id="u1",
        charge_at=charge_at,
        tokens=["tok1"],
        pref=pref,
        now=NOW_UTC,
    )
    assert row is not None
    assert row["scheduled_for_utc"] == NOW_UTC  # clamped, fires next tick


def test_build_row_skips_when_charge_already_passed():
    svc = CronTrialPushService()
    pref = {"language": "en", "timezone": "UTC", "gender": "male"}
    row = svc._build_row(
        user_id="u1",
        charge_at=NOW_UTC - timedelta(hours=1),
        tokens=["tok1"],
        pref=pref,
        now=NOW_UTC,
    )
    assert row is None


def test_build_row_skips_when_charge_unknown():
    svc = CronTrialPushService()
    pref = {"language": "en", "timezone": "UTC", "gender": "male"}
    row = svc._build_row(
        user_id="u1",
        charge_at=None,
        tokens=["tok1"],
        pref=pref,
        now=NOW_UTC,
    )
    assert row is None
