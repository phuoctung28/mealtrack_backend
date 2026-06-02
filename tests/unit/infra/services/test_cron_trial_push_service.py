"""Unit tests for CronTrialPushService."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from src.infra.services.cron_trial_push_service import (
    CronTrialPushService,
)

NOW_UTC = datetime(2026, 5, 17, 5, 0, 0, tzinfo=timezone.utc)


def _make_sub(user_id: str, expires_at: datetime, status: str = "active"):
    sub = MagicMock()
    sub.user_id = user_id
    sub.status = status
    sub.expires_at = expires_at
    return sub


def _patch_uow_with_subs(subs):
    """Build a context-manager mock for UnitOfWork wired to return `subs`."""
    uow_cm = MagicMock()
    uow_cm.subscriptions.find_expiring_in_window.return_value = subs
    uow_cm.session = MagicMock()
    uow_cm.session.execute.return_value.rowcount = len(subs)

    uow_ctx = MagicMock()
    uow_ctx.__enter__.return_value = uow_cm
    uow_ctx.__exit__.return_value = False
    return uow_ctx, uow_cm


def test_schedules_row_for_active_expiring_sub_with_token():
    svc = CronTrialPushService()
    user_id = str(uuid.uuid4())
    sub = _make_sub(user_id, NOW_UTC + timedelta(days=2, hours=6))

    uow_ctx, _uow = _patch_uow_with_subs([sub])

    with patch(
        "src.infra.services.cron_trial_push_service.UnitOfWork",
        return_value=uow_ctx,
    ), patch.object(
        CronTrialPushService,
        "_fetch_prefs",
        return_value={
            user_id: {
                "lunch_time_minutes": 720,
                "language": "en",
                "timezone": "Asia/Ho_Chi_Minh",
                "gender": "male",
            }
        },
    ), patch.object(
        CronTrialPushService,
        "_fetch_fcm_tokens",
        return_value={user_id: ["tok1", "tok2"]},
    ):
        n = svc.check_and_schedule_pushes(NOW_UTC)
        assert n >= 1


def test_skips_user_without_fcm_token():
    svc = CronTrialPushService()
    user_id = str(uuid.uuid4())
    sub = _make_sub(user_id, NOW_UTC + timedelta(days=2))

    uow_ctx, _uow = _patch_uow_with_subs([sub])

    with patch(
        "src.infra.services.cron_trial_push_service.UnitOfWork",
        return_value=uow_ctx,
    ), patch.object(
        CronTrialPushService,
        "_fetch_prefs",
        return_value={
            user_id: {
                "lunch_time_minutes": 720,
                "language": "en",
                "timezone": "UTC",
                "gender": "male",
            }
        },
    ), patch.object(
        CronTrialPushService,
        "_fetch_fcm_tokens",
        return_value={},  # no tokens
    ):
        n = svc.check_and_schedule_pushes(NOW_UTC)
        assert n == 0


def test_returns_zero_when_no_subs_in_window():
    svc = CronTrialPushService()
    uow_ctx, _uow = _patch_uow_with_subs([])
    with patch(
        "src.infra.services.cron_trial_push_service.UnitOfWork",
        return_value=uow_ctx,
    ):
        assert svc.check_and_schedule_pushes(NOW_UTC) == 0


def test_compute_scheduled_at_uses_lunch_plus_30():
    out_utc, _ = CronTrialPushService._compute_scheduled_at(
        now_utc=NOW_UTC,                                 # 05:00 UTC = 12:00 ICT
        tz=ZoneInfo("Asia/Ho_Chi_Minh"),
        lunch_time_minutes=720,                          # 12:00 local
    )
    local = out_utc.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    assert local.hour == 12 and local.minute == 30


def test_compute_scheduled_at_fallback_noon_when_lunch_missing():
    out_utc, _ = CronTrialPushService._compute_scheduled_at(
        now_utc=NOW_UTC,
        tz=ZoneInfo("Asia/Ho_Chi_Minh"),
        lunch_time_minutes=None,
    )
    local = out_utc.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    assert local.hour == 12 and local.minute == 0


def test_compute_scheduled_at_returns_local_date_not_utc_date():
    """05:00 UTC on May 17 = 12:00 May 17 ICT; scheduled_date must be local."""
    _, scheduled_date = CronTrialPushService._compute_scheduled_at(
        now_utc=NOW_UTC,
        tz=ZoneInfo("Asia/Ho_Chi_Minh"),
        lunch_time_minutes=720,
    )
    assert scheduled_date.isoformat() == "2026-05-17"


def test_runs_both_windows():
    svc = CronTrialPushService()
    with patch.object(svc, "_schedule_window", return_value=0) as sw:
        svc.check_and_schedule_pushes(NOW_UTC)
        assert sw.call_count == 2
        called_days = sorted(
            (c.kwargs.get("days_left") if "days_left" in c.kwargs else c.args[1])
            for c in sw.call_args_list
        )
        assert called_days == [1, 2]


def test_language_resolution_falls_back_to_users_language_code():
    """pref.language=None + users.language_code='vi' → 'vi' (not 'en')."""
    session = MagicMock()
    row = MagicMock()
    row.user_id = "u1"
    row.lunch_time_minutes = 720
    row.language = None
    row.timezone = "Asia/Ho_Chi_Minh"
    row.gender = "female"
    row.language_code = "vi"
    session.execute.return_value.fetchall.return_value = [row]

    out = CronTrialPushService._fetch_prefs(session, ["u1"])
    assert out["u1"]["language"] == "vi"


def test_language_resolution_pref_overrides_user():
    session = MagicMock()
    row = MagicMock()
    row.user_id = "u1"
    row.lunch_time_minutes = 720
    row.language = "en"
    row.timezone = "UTC"
    row.gender = "male"
    row.language_code = "vi"
    session.execute.return_value.fetchall.return_value = [row]

    out = CronTrialPushService._fetch_prefs(session, ["u1"])
    assert out["u1"]["language"] == "en"


def test_language_resolution_unknown_falls_back_to_en():
    session = MagicMock()
    row = MagicMock()
    row.user_id = "u1"
    row.lunch_time_minutes = 720
    row.language = "fr"
    row.timezone = "UTC"
    row.gender = "male"
    row.language_code = "de"
    session.execute.return_value.fetchall.return_value = [row]

    out = CronTrialPushService._fetch_prefs(session, ["u1"])
    assert out["u1"]["language"] == "en"


def test_build_row_skips_if_scheduled_time_already_passed():
    """Mid-day midnight-trigger run shouldn't insert a row that fires in the past."""
    svc = CronTrialPushService()
    user_id = "u1"
    # User in UTC, lunch_time=00 → fires at 00:30 UTC. `now` is 05:00 UTC.
    pref = {
        "lunch_time_minutes": 0,
        "language": "en",
        "timezone": "UTC",
        "gender": "male",
    }
    row = svc._build_row(
        user_id=user_id,
        days_left=2,
        tokens=["tok1"],
        pref=pref,
        now=NOW_UTC,
    )
    assert row is None


def test_build_row_returns_full_row_when_in_future():
    svc = CronTrialPushService()
    pref = {
        "lunch_time_minutes": 720,
        "language": "vi",
        "timezone": "Asia/Ho_Chi_Minh",
        "gender": "female",
    }
    row = svc._build_row(
        user_id="u1",
        days_left=1,
        tokens=["tok1"],
        pref=pref,
        now=NOW_UTC,
    )
    assert row is not None
    assert row["notification_type"] == "trial_expiry_1d"
    assert row["status"] == "pending"
    assert row["context"]["language_code"] == "vi"
    assert row["context"]["gender"] == "female"
    assert row["context"]["fcm_tokens"] == ["tok1"]
    assert row["expires_at"] == row["scheduled_for_utc"] + timedelta(days=2)
