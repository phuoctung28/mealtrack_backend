import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_detects_midnight_timezone():
    from src.infra.services.scheduled_notification_service import _timezones_at_midnight

    # 2026-04-22 17:00 UTC = 2026-04-23 00:00 Asia/Ho_Chi_Minh (UTC+7)
    now = datetime(2026, 4, 22, 17, 0, 0, tzinfo=timezone.utc)
    result = _timezones_at_midnight(["Asia/Ho_Chi_Minh", "UTC"], now)
    assert "Asia/Ho_Chi_Minh" in result
    assert "UTC" not in result


@pytest.mark.asyncio
async def test_send_loop_marks_notifications_sent():
    from src.infra.services.scheduled_notification_service import (
        ScheduledNotificationService,
    )

    mock_notif = MagicMock()
    mock_notif.notification_type = "meal_reminder_lunch"
    mock_notif.context = {
        "fcm_tokens": ["tok1"],
        "calorie_goal": 1800,
        "gender": "male",
        "language_code": "en",
    }
    mock_notif.id = "notif-id-1"
    mock_notif.user_id = "user-1"

    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._firebase = mock_firebase
    svc._running = True

    with patch(
        "src.infra.services.scheduled_notification_service.ReminderQueryBuilder"
    ) as mock_qb, patch(
        "src.infra.services.scheduled_notification_service.UnitOfWork"
    ) as mock_uow, patch(
        "src.infra.services.scheduled_notification_service._fetch_calories_consumed_batch",
        return_value={"user-1": 400},
    ):
        mock_qb.find_due_notifications.return_value = [mock_notif]
        mock_uow.return_value.__enter__.return_value.session = MagicMock()

        now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=timezone.utc)
        await svc._send_due_notifications(now)

    mock_firebase.send_multicast.assert_called_once()
    assert mock_notif.status == "processing"
    assert mock_firebase.send_multicast.call_args.kwargs["data"] == {
        "notification_ids": "notif-id-1",
        "notification_count": "1",
    }
    call_kwargs = mock_firebase.send_multicast.call_args.kwargs
    assert "1400" in call_kwargs.get("body", ""), (
        f"Expected remaining=1400 in body, got: {call_kwargs.get('body')}"
    )


def test_render_message_daily_summary_zero_logs():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message(
        "daily_summary", 2000, "male", "en", calories_consumed=0, calorie_goal=2000
    )
    assert title == "Nutree"
    assert "Busy" in body
    assert "log" in body.lower()


def test_render_message_daily_summary_on_target():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message(
        "daily_summary", 0, "male", "en", calories_consumed=1980, calorie_goal=2000
    )
    assert "99%" in body


def test_render_message_daily_summary_under_goal():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message(
        "daily_summary", 500, "male", "en", calories_consumed=1500, calorie_goal=2000
    )
    assert "500" in body


def test_render_message_daily_summary_slightly_over():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message(
        "daily_summary", 0, "male", "en", calories_consumed=2200, calorie_goal=2000
    )
    assert "200" in body


def test_render_message_daily_summary_way_over():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message(
        "daily_summary", 0, "male", "en", calories_consumed=2600, calorie_goal=2000
    )
    assert "600" in body


@pytest.mark.asyncio
async def test_startup_catchup_calls_precompute_for_each_timezone():
    from src.infra.services.scheduled_notification_service import (
        ScheduledNotificationService,
    )

    mock_precompute = AsyncMock()
    mock_precompute.precompute_for_timezone = AsyncMock()

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._precompute = mock_precompute
    svc._distinct_timezones = ["UTC", "Asia/Ho_Chi_Minh"]
    svc._trial_push = None  # disable trial-push branch for this test

    await svc._startup_catchup()

    assert mock_precompute.precompute_for_timezone.call_count == 2


# ── Trial-expiry coverage ──────────────────────────────────────────────────────


def test_render_trial_expiry_2d_en_male_returns_2_day_body():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message("trial_expiry_2d", 0, "male", "en")
    assert title == "Nutree"
    assert "2 days" in body


def test_render_trial_expiry_1d_en_female_returns_1_day_body():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message("trial_expiry_1d", 0, "female", "en")
    assert title == "Nutree"
    assert "tomorrow" in body.lower()


def test_render_trial_expiry_2d_vi_male_returns_vietnamese():
    from src.infra.services.scheduled_notification_service import _render_message

    title, body = _render_message("trial_expiry_2d", 0, "male", "vi")
    assert "2 ngày" in body
    assert "bro" in body


def test_render_trial_expiry_1d_vi_female_returns_vietnamese():
    from src.infra.services.scheduled_notification_service import _render_message

    _, body = _render_message("trial_expiry_1d", 0, "female", "vi")
    assert "bạn ơi" in body
    assert "mai" in body.lower()


def test_render_unknown_type_falls_through_to_generic_stub():
    from src.infra.services.scheduled_notification_service import _render_message

    _, body = _render_message("totally_unknown", 0, "male", "en")
    assert body == "You have a notification 📬"


def test_seconds_until_next_minute_aligns_scheduler_tick():
    from src.infra.services.scheduled_notification_service import (
        _seconds_until_next_minute,
    )

    now = datetime(2026, 4, 22, 5, 0, 58, 500_000, tzinfo=timezone.utc)

    assert _seconds_until_next_minute(now) == 1.5


def _make_trial_notif(notif_type: str = "trial_expiry_2d"):
    n = MagicMock()
    n.id = "n1"
    n.user_id = "u1"
    n.notification_type = notif_type
    n.context = {
        "fcm_tokens": ["tok1"],
        "calorie_goal": 2000,
        "calories_consumed": 0,
        "gender": "male",
        "language_code": "en",
    }
    return n


@pytest.mark.asyncio
async def test_send_due_normalizes_trial_fcm_type():
    """trial_expiry_2d in DB → 'trial_expiry' in FCM data.type."""
    import asyncio as _asyncio

    from src.infra.services.scheduled_notification_service import (
        ScheduledNotificationService,
    )

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._firebase = MagicMock()
    svc._firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )
    svc._running = True

    async def _passthrough(fn, *a, **kw):
        return fn(*a, **kw)

    with patch(
        "src.infra.services.scheduled_notification_service.ReminderQueryBuilder"
    ) as Q, patch(
        "src.infra.services.scheduled_notification_service.UnitOfWork"
    ), patch.object(
        _asyncio, "to_thread", new=_passthrough
    ):
        Q.find_due_notifications.return_value = [_make_trial_notif("trial_expiry_2d")]
        await svc._send_due_notifications(datetime(2026, 5, 17, tzinfo=timezone.utc))

    call_kwargs = svc._firebase.send_multicast.call_args.kwargs
    assert call_kwargs["notification_type"] == "trial_expiry"


@pytest.mark.asyncio
async def test_send_due_trial_skips_redis_lookup(caplog):
    """Trial rows must NOT log Redis cache-miss WARNING."""
    import asyncio as _asyncio

    from src.infra.services.scheduled_notification_service import (
        ScheduledNotificationService,
    )

    svc = ScheduledNotificationService.__new__(ScheduledNotificationService)
    svc._firebase = MagicMock()
    svc._firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )
    svc._running = True

    async def _passthrough(fn, *a, **kw):
        return fn(*a, **kw)

    with patch(
        "src.infra.services.scheduled_notification_service.ReminderQueryBuilder"
    ) as Q, patch(
        "src.infra.services.scheduled_notification_service.UnitOfWork"
    ), patch.object(
        _asyncio, "to_thread", new=_passthrough
    ):
        Q.find_due_notifications.return_value = [_make_trial_notif("trial_expiry_1d")]
        with caplog.at_level("WARNING"):
            await svc._send_due_notifications(
                datetime(2026, 5, 17, tzinfo=timezone.utc)
            )

    assert "Redis cache miss" not in caplog.text


def test_build_notification_rows_includes_hydration_reminders_when_enabled():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
        _DEFAULT_AFTERNOON_MINUTES,
        _DEFAULT_EVENING_MINUTES,
    )

    svc = DailyContextPrecomputeService.__new__(DailyContextPrecomputeService)
    svc._tdee_service = MagicMock()

    pref = MagicMock()
    pref.user_id = "user-1"
    pref.meal_reminders_enabled = False
    pref.daily_summary_enabled = False
    pref.hydration_reminders_enabled = True
    pref.language = "en"

    tokens_by_user = {"user-1": ["tok1"]}
    profiles_by_user = {"user-1": MagicMock(gender="male", language_code="en")}
    today = date(2026, 5, 23)

    rows = svc._build_notification_rows(
        pref_rows=[pref],
        tokens_by_user=tokens_by_user,
        calorie_goals={"user-1": 2000},
        consumed_by_user={"user-1": 0},
        profiles_by_user=profiles_by_user,
        today=today,
        tz_name="UTC",
    )

    types = [r["notification_type"] for r in rows]
    assert "hydration_reminder_afternoon" in types
    assert "hydration_reminder_evening" in types


def test_build_notification_rows_skips_hydration_when_disabled():
    from src.infra.services.daily_context_precompute_service import DailyContextPrecomputeService

    svc = DailyContextPrecomputeService.__new__(DailyContextPrecomputeService)
    svc._tdee_service = MagicMock()

    pref = MagicMock()
    pref.user_id = "user-2"
    pref.meal_reminders_enabled = False
    pref.daily_summary_enabled = False
    pref.hydration_reminders_enabled = False
    pref.language = "en"

    rows = svc._build_notification_rows(
        pref_rows=[pref],
        tokens_by_user={"user-2": ["tok1"]},
        calorie_goals={"user-2": 2000},
        consumed_by_user={"user-2": 0},
        profiles_by_user={"user-2": MagicMock(gender="male", language_code="en")},
        today=date(2026, 5, 23),
        tz_name="UTC",
    )

    types = [r["notification_type"] for r in rows]
    assert "hydration_reminder_afternoon" not in types
    assert "hydration_reminder_evening" not in types
