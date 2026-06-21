"""Unit tests for the push notification cron entry point."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_async_engine(timezones=None):
    engine = MagicMock()
    connect_cm = AsyncMock()
    conn = AsyncMock()
    warmup_result = MagicMock()
    tz_result = MagicMock()
    tz_result.fetchall.return_value = [
        MagicMock(timezone=tz) for tz in (timezones or [])
    ]
    conn.execute = AsyncMock(side_effect=[warmup_result, tz_result])
    connect_cm.__aenter__.return_value = conn
    connect_cm.__aexit__.return_value = False
    engine.connect.return_value = connect_cm
    engine.dispose = AsyncMock()
    return engine


@pytest.mark.asyncio
async def test_push_cron_happy_path_runs_all_phases():
    """All cron phases execute when DB is reachable."""
    with (
        patch("src.cron.push.initialize_observability"),
        patch(
            "src.cron.push.async_engine",
            _mock_async_engine(["Asia/Ho_Chi_Minh", "UTC"]),
        ) as mock_engine,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.OnboardingRetentionCampaignScheduler") as mock_campaign_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_svc_cls,
        patch("src.cron.push.flush_observability"),
    ):
        # Precompute service
        mock_precompute = AsyncMock()
        mock_precompute.precompute_for_timezone = AsyncMock()
        mock_precompute_cls.return_value = mock_precompute

        # Trial push service
        mock_trial = AsyncMock()
        mock_trial.check_and_schedule_pushes = AsyncMock()
        mock_trial_cls.return_value = mock_trial

        # Campaign scheduler (Phase 2.5)
        mock_campaign = AsyncMock()
        mock_campaign.schedule = AsyncMock(return_value=0)
        mock_campaign_cls.return_value = mock_campaign

        # FCM dispatch service
        mock_svc = MagicMock()
        mock_svc._send_due_notifications = AsyncMock()
        mock_svc.cleanup_expired_notifications = AsyncMock()
        mock_svc_cls.return_value = mock_svc

        from src.cron.push import run

        await run()

        # All phases were invoked
        assert mock_precompute.precompute_for_timezone.call_count == 2
        mock_trial.check_and_schedule_pushes.assert_awaited_once()
        mock_campaign.schedule.assert_awaited_once()
        mock_svc._send_due_notifications.assert_called_once()
        mock_svc.cleanup_expired_notifications.assert_awaited_once()
        mock_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_push_cron_aborts_on_db_warmup_failure():
    """Early exit when DB warm-up fails — no phases run."""
    with (
        patch("src.cron.push.initialize_observability"),
        patch("src.cron.push.async_engine", _mock_async_engine()) as mock_engine,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_svc_cls,
        patch("src.cron.push.flush_observability"),
        patch("src.cron.push.capture_exception") as mock_capture_exception,
    ):
        mock_engine.connect.side_effect = Exception("Neon cold start")

        from src.cron.push import run

        await run()  # should not raise

        mock_precompute_cls.assert_not_called()
        mock_trial_cls.assert_not_called()
        mock_svc_cls.assert_not_called()
        mock_capture_exception.assert_called_once()


@pytest.mark.asyncio
async def test_push_cron_phase_failure_does_not_abort_subsequent_phases():
    """A failure in Phase 1 does not prevent Phase 2 or Phase 3 from running."""
    with (
        patch("src.cron.push.initialize_observability"),
        patch("src.cron.push.async_engine", _mock_async_engine()) as mock_engine,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService"),
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_svc_cls,
        patch("src.cron.push.OnboardingRetentionCampaignScheduler") as mock_campaign_cls,
        patch("src.cron.push.flush_observability"),
        patch("src.cron.push.capture_exception") as mock_capture_exception,
    ):
        # Phase 1 raises
        mock_engine.connect.side_effect = [
            mock_engine.connect.return_value,
            RuntimeError("db error"),
        ]

        # Phase 2 and 3 services
        mock_trial = AsyncMock()
        mock_trial.check_and_schedule_pushes = AsyncMock()
        mock_trial_cls.return_value = mock_trial

        mock_campaign = AsyncMock()
        mock_campaign.schedule = AsyncMock(return_value=0)
        mock_campaign_cls.return_value = mock_campaign

        mock_svc = MagicMock()
        mock_svc._send_due_notifications = AsyncMock()
        mock_svc.cleanup_expired_notifications = AsyncMock()
        mock_svc_cls.return_value = mock_svc

        from src.cron.push import run

        await run()  # must not raise

        mock_trial.check_and_schedule_pushes.assert_awaited_once()
        mock_svc._send_due_notifications.assert_called_once()
        mock_svc.cleanup_expired_notifications.assert_awaited_once()
        mock_capture_exception.assert_called_once()
