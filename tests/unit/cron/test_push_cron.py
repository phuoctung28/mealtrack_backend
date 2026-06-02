"""Unit tests for the push notification cron entry point."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_push_cron_happy_path_runs_all_phases():
    """All cron phases execute when DB is reachable."""
    with (
        patch("src.cron.push.initialize_sentry"),
        patch("src.cron.push.engine") as mock_engine,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_svc_cls,
        patch("src.cron.push.UnitOfWork") as mock_uow_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up succeeds
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # UoW returns timezone rows
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = [
            MagicMock(timezone="Asia/Ho_Chi_Minh"),
            MagicMock(timezone="UTC"),
        ]
        mock_uow_cls.return_value.__enter__ = MagicMock(
            return_value=MagicMock(session=mock_session)
        )
        mock_uow_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Precompute service
        mock_precompute = AsyncMock()
        mock_precompute.precompute_for_timezone = AsyncMock()
        mock_precompute_cls.return_value = mock_precompute

        # Trial push service
        mock_trial = MagicMock()
        mock_trial.check_and_schedule_pushes = MagicMock()
        mock_trial_cls.return_value = mock_trial

        # FCM dispatch service
        mock_svc = MagicMock()
        mock_svc._send_due_notifications = AsyncMock()
        mock_svc.cleanup_expired_notifications = MagicMock()
        mock_svc_cls.return_value = mock_svc

        from src.cron.push import run
        await run()

        # All phases were invoked
        assert mock_precompute.precompute_for_timezone.call_count == 2
        mock_trial.check_and_schedule_pushes.assert_called_once()
        mock_svc._send_due_notifications.assert_called_once()
        mock_svc.cleanup_expired_notifications.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_push_cron_aborts_on_db_warmup_failure():
    """Early exit when DB warm-up fails — no phases run."""
    with (
        patch("src.cron.push.initialize_sentry"),
        patch("src.cron.push.engine") as mock_engine,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService") as mock_precompute_cls,
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_svc_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up raises
        mock_engine.connect.side_effect = Exception("Neon cold start")

        from src.cron.push import run
        await run()  # should not raise

        mock_precompute_cls.assert_not_called()
        mock_trial_cls.assert_not_called()
        mock_svc_cls.assert_not_called()


@pytest.mark.asyncio
async def test_push_cron_phase_failure_does_not_abort_subsequent_phases():
    """A failure in Phase 1 does not prevent Phase 2 or Phase 3 from running."""
    with (
        patch("src.cron.push.initialize_sentry"),
        patch("src.cron.push.engine") as mock_engine,
        patch("src.cron.push.FirebaseService"),
        patch("src.cron.push.DailyContextPrecomputeService"),
        patch("src.cron.push.CronTrialPushService") as mock_trial_cls,
        patch("src.cron.push.CronNotificationDispatchService") as mock_svc_cls,
        patch("src.cron.push.UnitOfWork") as mock_uow_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up succeeds
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        # Phase 1 raises
        mock_uow_cls.return_value.__enter__ = MagicMock(
            side_effect=RuntimeError("db error")
        )
        mock_uow_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Phase 2 and 3 services
        mock_trial = MagicMock()
        mock_trial.check_and_schedule_pushes = MagicMock()
        mock_trial_cls.return_value = mock_trial

        mock_svc = MagicMock()
        mock_svc._send_due_notifications = AsyncMock()
        mock_svc.cleanup_expired_notifications = MagicMock()
        mock_svc_cls.return_value = mock_svc

        from src.cron.push import run
        await run()  # must not raise

        mock_trial.check_and_schedule_pushes.assert_called_once()
        mock_svc._send_due_notifications.assert_called_once()
        mock_svc.cleanup_expired_notifications.assert_called_once()
