"""Failing contract tests verifying that push.py cron wires the campaign scheduler.

The production module `OnboardingRetentionCampaignScheduler` does not exist yet —
imports from `src.cron.push` will fail until Phase 2 adds the scheduler call there.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_async_engine(timezones=None):
    """Build an async engine mock that returns warmup + timezone rows."""
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
async def test_cron_push_calls_campaign_scheduler():
    """push.run() must invoke OnboardingRetentionCampaignScheduler.schedule()."""
    with (
        patch("src.cron.push.initialize_observability"),
        patch(
            "src.cron.push.async_engine",
            _mock_async_engine(["UTC"]),
        ),
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_dispatch_cls,
        patch(
            "src.cron.push.OnboardingRetentionCampaignScheduler"
        ) as mock_campaign_cls,
        patch("src.cron.push.flush_observability"),
    ):
        mock_precompute = AsyncMock()
        mock_precompute.precompute_for_timezone = AsyncMock()
        mock_precompute_cls.return_value = mock_precompute

        mock_trial = AsyncMock()
        mock_trial.check_and_schedule_pushes = AsyncMock()
        mock_trial_cls.return_value = mock_trial

        mock_dispatch = MagicMock()
        mock_dispatch._send_due_notifications = AsyncMock()
        mock_dispatch.cleanup_expired_notifications = AsyncMock()
        mock_dispatch_cls.return_value = mock_dispatch

        mock_campaign = AsyncMock()
        mock_campaign.schedule = AsyncMock(return_value=0)
        mock_campaign_cls.return_value = mock_campaign

        from src.cron.push import run

        await run()

        # Campaign scheduler must have been called during the cron run
        mock_campaign.schedule.assert_awaited_once()


@pytest.mark.asyncio
async def test_campaign_scheduler_exception_does_not_stop_dispatch():
    """If campaign scheduler raises, FCM dispatch still runs (isolated try/except)."""
    with (
        patch("src.cron.push.initialize_observability"),
        patch(
            "src.cron.push.async_engine",
            _mock_async_engine(["UTC"]),
        ),
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_dispatch_cls,
        patch(
            "src.cron.push.OnboardingRetentionCampaignScheduler"
        ) as mock_campaign_cls,
        patch("src.cron.push.flush_observability"),
        patch("src.cron.push.capture_exception"),
    ):
        mock_precompute = AsyncMock()
        mock_precompute.precompute_for_timezone = AsyncMock()
        mock_precompute_cls.return_value = mock_precompute

        mock_trial = AsyncMock()
        mock_trial.check_and_schedule_pushes = AsyncMock()
        mock_trial_cls.return_value = mock_trial

        mock_dispatch = MagicMock()
        mock_dispatch._send_due_notifications = AsyncMock()
        mock_dispatch.cleanup_expired_notifications = AsyncMock()
        mock_dispatch_cls.return_value = mock_dispatch

        # Campaign scheduler explodes
        mock_campaign = AsyncMock()
        mock_campaign.schedule = AsyncMock(side_effect=RuntimeError("campaign boom"))
        mock_campaign_cls.return_value = mock_campaign

        from src.cron.push import run

        await run()  # must not propagate

        # Dispatch must still have run despite the campaign scheduler failure
        mock_dispatch._send_due_notifications.assert_called_once()
        mock_dispatch.cleanup_expired_notifications.assert_awaited_once()
