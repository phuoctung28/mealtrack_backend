from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_loop_marks_notifications_sent():
    from src.infra.services.cron_notification_dispatch_service import (
        CronNotificationDispatchService,
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

    svc = CronNotificationDispatchService.__new__(CronNotificationDispatchService)
    svc._firebase = mock_firebase
    svc._recover_stale_processing = AsyncMock()
    async def _claim_due(_now):
        mock_notif.status = "processing"
        return [mock_notif]

    svc._claim_due_notifications = AsyncMock(side_effect=_claim_due)
    svc._mark_notifications = AsyncMock()

    with patch(
        "src.infra.services.cron_notification_dispatch_service._fetch_calories_consumed_batch",
        AsyncMock(return_value={"user-1": 400}),
    ):
        now = datetime(2026, 4, 22, 5, 0, 0, tzinfo=UTC)
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


@pytest.mark.asyncio
async def test_wholesale_fcm_failure_requeues_instead_of_marking_sent():
    """A whole-batch FCM failure must requeue rows (pending), never mark 'sent'.

    Regression guard: send_multicast returning success=False with no failed_tokens
    (transient Firebase/network/auth outage) previously marked the notification
    'sent' with zero delivery and no retry. The row must go to retry_ids instead.
    """
    from src.infra.services.cron_notification_dispatch_service import (
        CronNotificationDispatchService,
    )

    mock_notif = MagicMock()
    mock_notif.notification_type = "trial_expiry_2d"
    mock_notif.context = {
        "fcm_tokens": ["tok1"],
        "gender": "male",
        "language_code": "en",
    }
    mock_notif.id = "trial-notif-1"
    mock_notif.user_id = "user-1"

    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(
        return_value={"success": False, "reason": "send_error"}
    )

    svc = CronNotificationDispatchService.__new__(CronNotificationDispatchService)
    svc._firebase = mock_firebase
    svc._recover_stale_processing = AsyncMock()
    svc._claim_due_notifications = AsyncMock(return_value=[mock_notif])
    svc._mark_notifications = AsyncMock()

    await svc._send_due_notifications(datetime(2026, 5, 17, tzinfo=UTC))

    mock_firebase.send_multicast.assert_called_once()
    sent_ids, failed_ids, retry_ids = svc._mark_notifications.call_args.args
    assert "trial-notif-1" not in sent_ids, "must not mark sent on FCM failure"
    assert "trial-notif-1" in retry_ids, "must requeue for retry on FCM failure"


def test_render_message_daily_summary_zero_logs():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message(
        "daily_summary", 2000, "male", "en", calories_consumed=0, calorie_goal=2000
    )
    assert title == "Nutree"
    assert "busy" in body.lower()
    assert "log" in body.lower()


@pytest.mark.parametrize(
    "notification_type,kwargs",
    [
        ("meal_reminder_breakfast", {}),
        ("meal_reminder_lunch", {}),
        ("meal_reminder_dinner", {}),
        ("daily_summary", {"calories_consumed": 0, "calorie_goal": 2000}),
        ("trial_expiry_2d", {}),
        ("trial_expiry_1d", {}),
        (
            "hydration_reminder_afternoon",
            {"consumed_ml": 500, "goal_ml": 2000, "remaining_ml": 1500},
        ),
        (
            "hydration_reminder_evening",
            {"consumed_ml": 1200, "goal_ml": 2000, "remaining_ml": 800},
        ),
    ],
)
def test_render_known_notification_types_have_ios_display_text(
    notification_type, kwargs
):
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message(notification_type, 1000, "male", "en", **kwargs)

    assert title.strip()
    assert body.strip()


def test_render_message_daily_summary_on_target():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message(
        "daily_summary", 0, "male", "en", calories_consumed=1980, calorie_goal=2000
    )
    assert "99%" in body


def test_render_message_daily_summary_under_goal():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message(
        "daily_summary", 500, "male", "en", calories_consumed=1500, calorie_goal=2000
    )
    assert "500" in body


def test_render_message_daily_summary_slightly_over():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message(
        "daily_summary", 0, "male", "en", calories_consumed=2200, calorie_goal=2000
    )
    assert "200" in body


def test_render_message_daily_summary_way_over():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message(
        "daily_summary", 0, "male", "en", calories_consumed=2600, calorie_goal=2000
    )
    assert "600" in body


# ── Trial-expiry coverage ──────────────────────────────────────────────────────


def test_render_trial_expiry_2d_en_male_returns_2_day_body():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message("trial_expiry_2d", 0, "male", "en")
    assert title == "Nutree"
    assert "48 hours" in body


def test_render_trial_expiry_1d_en_female_returns_1_day_body():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message("trial_expiry_1d", 0, "female", "en")
    assert title == "Nutree"
    assert "tomorrow" in body.lower()


def test_render_trial_expiry_2d_vi_male_returns_vietnamese():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    title, body = _render_message("trial_expiry_2d", 0, "male", "vi")
    assert "48 giờ" in body
    assert "bro" in body


def test_render_trial_expiry_1d_vi_female_returns_vietnamese():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    _, body = _render_message("trial_expiry_1d", 0, "female", "vi")
    assert "bạn" in body
    assert "reset" in body.lower()


def test_render_unknown_type_falls_through_to_generic_stub():
    from src.infra.services.cron_notification_dispatch_service import _render_message

    _, body = _render_message("totally_unknown", 0, "male", "en")
    assert body == "You have a notification 📬"


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
    from src.infra.services.cron_notification_dispatch_service import (
        CronNotificationDispatchService,
    )

    svc = CronNotificationDispatchService.__new__(CronNotificationDispatchService)
    svc._firebase = MagicMock()
    svc._firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )
    svc._recover_stale_processing = AsyncMock()
    svc._claim_due_notifications = AsyncMock(
        return_value=[_make_trial_notif("trial_expiry_2d")]
    )
    svc._mark_notifications = AsyncMock()

    await svc._send_due_notifications(datetime(2026, 5, 17, tzinfo=UTC))

    call_kwargs = svc._firebase.send_multicast.call_args.kwargs
    assert call_kwargs["notification_type"] == "trial_expiry"


@pytest.mark.asyncio
async def test_send_due_trial_skips_redis_lookup(caplog):
    """Trial rows must NOT log Redis cache-miss WARNING."""
    from src.infra.services.cron_notification_dispatch_service import (
        CronNotificationDispatchService,
    )

    svc = CronNotificationDispatchService.__new__(CronNotificationDispatchService)
    svc._firebase = MagicMock()
    svc._firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )
    svc._recover_stale_processing = AsyncMock()
    svc._claim_due_notifications = AsyncMock(
        return_value=[_make_trial_notif("trial_expiry_1d")]
    )
    svc._mark_notifications = AsyncMock()

    with caplog.at_level("WARNING"):
        await svc._send_due_notifications(datetime(2026, 5, 17, tzinfo=UTC))

    assert "Redis cache miss" not in caplog.text


def test_build_notification_rows_includes_hydration_reminders_when_enabled():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
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


@pytest.mark.asyncio
async def test_hydration_reminder_skipped_when_above_threshold():
    """Afternoon reminder skipped when user has consumed >= 50% of goal."""
    from datetime import datetime
    from unittest.mock import MagicMock, patch

    from src.infra.services.cron_notification_dispatch_service import (
        CronNotificationDispatchService,
    )

    mock_notif = MagicMock()
    mock_notif.notification_type = "hydration_reminder_afternoon"
    mock_notif.context = {
        "fcm_tokens": ["tok1"],
        "gender": "male",
        "language_code": "en",
    }
    mock_notif.id = "hydration-notif-1"
    mock_notif.user_id = "user-h1"

    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )

    svc = CronNotificationDispatchService.__new__(CronNotificationDispatchService)
    svc._firebase = mock_firebase
    svc._recover_stale_processing = AsyncMock()
    svc._claim_due_notifications = AsyncMock(return_value=[mock_notif])
    svc._mark_notifications = AsyncMock()

    # consumed_ml=1500, goal_ml=2000 → 75% → above 50% afternoon threshold → skip FCM
    with patch(
        "src.infra.services.cron_notification_dispatch_service._fetch_hydration_data_batch",
        AsyncMock(return_value={"user-h1": (1500, 2000)}),
    ):
        now = datetime(2026, 5, 23, 6, 0, 0, tzinfo=UTC)
        await svc._send_due_notifications(now)

    # FCM not called because threshold met
    mock_firebase.send_multicast.assert_not_called()


@pytest.mark.asyncio
async def test_hydration_reminder_sent_when_below_threshold():
    """Evening reminder fires when user has consumed < 80% of goal."""
    from datetime import datetime
    from unittest.mock import MagicMock, patch

    from src.infra.services.cron_notification_dispatch_service import (
        CronNotificationDispatchService,
    )

    mock_notif = MagicMock()
    mock_notif.notification_type = "hydration_reminder_evening"
    mock_notif.context = {
        "fcm_tokens": ["tok1"],
        "gender": "male",
        "language_code": "en",
    }
    mock_notif.id = "hydration-notif-2"
    mock_notif.user_id = "user-h2"

    mock_firebase = MagicMock()
    mock_firebase.send_multicast = MagicMock(
        return_value={"success": True, "failed_tokens": []}
    )

    svc = CronNotificationDispatchService.__new__(CronNotificationDispatchService)
    svc._firebase = mock_firebase
    svc._recover_stale_processing = AsyncMock()
    svc._claim_due_notifications = AsyncMock(return_value=[mock_notif])
    svc._mark_notifications = AsyncMock()

    # consumed_ml=1200, goal_ml=2000 → 60% → below 80% evening threshold → send
    with patch(
        "src.infra.services.cron_notification_dispatch_service._fetch_hydration_data_batch",
        AsyncMock(return_value={"user-h2": (1200, 2000)}),
    ):
        now = datetime(2026, 5, 23, 11, 0, 0, tzinfo=UTC)
        await svc._send_due_notifications(now)

    mock_firebase.send_multicast.assert_called_once()


def test_build_notification_rows_skips_hydration_when_disabled():
    from src.infra.services.daily_context_precompute_service import (
        DailyContextPrecomputeService,
    )

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
