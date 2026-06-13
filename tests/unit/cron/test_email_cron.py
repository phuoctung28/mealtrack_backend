"""Unit tests for the email notification cron entry point."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_async_engine():
    engine = MagicMock()
    conn_cm = AsyncMock()
    conn = AsyncMock()
    conn_cm.__aenter__.return_value = conn
    conn_cm.__aexit__.return_value = False
    engine.connect.return_value = conn_cm
    engine.dispose = AsyncMock()
    return engine


@pytest.mark.asyncio
async def test_email_cron_calls_check_and_send():
    """Happy path: DB reachable, emails are sent."""
    with (
        patch("src.cron.email.initialize_observability"),
        patch("src.cron.email.async_engine", _mock_async_engine()) as mock_engine,
        patch("src.cron.email.ResendEmailAdapter"),
        patch("src.cron.email.EmailTemplateRenderer"),
        patch("src.cron.email.EmailService"),
        patch("src.cron.email.CronLifecycleEmailService") as mock_ses_cls,
        patch("src.cron.email.flush_observability"),
    ):
        mock_ses = AsyncMock()
        mock_ses.check_and_send_emails = AsyncMock()
        mock_ses_cls.return_value = mock_ses

        from src.cron.email import run

        await run()

        mock_ses.check_and_send_emails.assert_called_once()
        mock_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_email_cron_aborts_on_db_warmup_failure():
    """Early exit when DB warm-up fails — no emails sent."""
    with (
        patch("src.cron.email.initialize_observability"),
        patch("src.cron.email.async_engine", _mock_async_engine()) as mock_engine,
        patch("src.cron.email.CronLifecycleEmailService") as mock_ses_cls,
        patch("src.cron.email.flush_observability"),
        patch("src.cron.email.capture_exception") as mock_capture_exception,
    ):
        mock_engine.connect.side_effect = Exception("DB down")

        from src.cron.email import run

        await run()  # must not raise

        mock_ses_cls.assert_not_called()
        mock_capture_exception.assert_called_once()


@pytest.mark.asyncio
async def test_email_cron_logs_error_on_send_failure():
    """Email send failure is caught and logged; cron exits cleanly."""
    with (
        patch("src.cron.email.initialize_observability"),
        patch("src.cron.email.async_engine", _mock_async_engine()) as mock_engine,
        patch("src.cron.email.ResendEmailAdapter"),
        patch("src.cron.email.EmailTemplateRenderer"),
        patch("src.cron.email.EmailService"),
        patch("src.cron.email.CronLifecycleEmailService") as mock_ses_cls,
        patch("src.cron.email.flush_observability"),
        patch("src.cron.email.capture_exception") as mock_capture_exception,
    ):
        mock_ses = AsyncMock()
        mock_ses.check_and_send_emails = AsyncMock(
            side_effect=RuntimeError("Resend down")
        )
        mock_ses_cls.return_value = mock_ses

        from src.cron.email import run

        await run()  # must not raise

        mock_engine.dispose.assert_awaited_once()
        mock_capture_exception.assert_called_once()
