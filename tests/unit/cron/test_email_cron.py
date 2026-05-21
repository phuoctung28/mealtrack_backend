"""Unit tests for the email notification cron entry point."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_email_cron_calls_check_and_send():
    """Happy path: DB reachable, emails are sent."""
    with (
        patch("src.cron.email.initialize_sentry"),
        patch("src.cron.email.engine") as mock_engine,
        patch("src.cron.email.async_engine", None),
        patch("src.cron.email.ResendEmailAdapter"),
        patch("src.cron.email.EmailTemplateRenderer"),
        patch("src.cron.email.EmailService"),
        patch("src.cron.email.ScheduledEmailService") as mock_ses_cls,
        patch("sentry_sdk.flush"),
    ):
        # DB warm-up succeeds
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_ses = AsyncMock()
        mock_ses.check_and_send_emails = AsyncMock()
        mock_ses_cls.return_value = mock_ses

        from src.cron.email import run
        await run()

        mock_ses.check_and_send_emails.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_email_cron_aborts_on_db_warmup_failure():
    """Early exit when DB warm-up fails — no emails sent."""
    with (
        patch("src.cron.email.initialize_sentry"),
        patch("src.cron.email.engine") as mock_engine,
        patch("src.cron.email.ScheduledEmailService") as mock_ses_cls,
        patch("sentry_sdk.flush"),
    ):
        mock_engine.connect.side_effect = Exception("DB down")

        from src.cron.email import run
        await run()  # must not raise

        mock_ses_cls.assert_not_called()


@pytest.mark.asyncio
async def test_email_cron_logs_error_on_send_failure():
    """Email send failure is caught and logged; cron exits cleanly."""
    with (
        patch("src.cron.email.initialize_sentry"),
        patch("src.cron.email.engine") as mock_engine,
        patch("src.cron.email.async_engine", None),
        patch("src.cron.email.ResendEmailAdapter"),
        patch("src.cron.email.EmailTemplateRenderer"),
        patch("src.cron.email.EmailService"),
        patch("src.cron.email.ScheduledEmailService") as mock_ses_cls,
        patch("sentry_sdk.flush"),
    ):
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        mock_ses = AsyncMock()
        mock_ses.check_and_send_emails = AsyncMock(side_effect=RuntimeError("Resend down"))
        mock_ses_cls.return_value = mock_ses

        from src.cron.email import run
        await run()  # must not raise

        mock_engine.dispose.assert_called_once()
