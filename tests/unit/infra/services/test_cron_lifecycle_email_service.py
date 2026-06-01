"""Tests for CronLifecycleEmailService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.ports.email_service_port import EmailResult
from src.infra.services.cron_lifecycle_email_service import CronLifecycleEmailService


@pytest.fixture
def mock_email_service():
    service = AsyncMock()
    service.send_reengagement_email.return_value = EmailResult(
        success=True, message_id="msg_1"
    )
    service.send_trial_expiring_email.return_value = EmailResult(
        success=True, message_id="msg_2"
    )
    return service


@pytest.fixture
def cron_service(mock_email_service):
    return CronLifecycleEmailService(email_service=mock_email_service)


@pytest.fixture
def inactive_user():
    user = MagicMock()
    user.id = "user_inactive"
    user.email = "inactive@example.com"
    user.first_name = "Inactive"
    user.email_opt_out = False
    user.last_accessed = datetime.now(timezone.utc) - timedelta(days=4)
    return user


@pytest.mark.asyncio
async def test_finds_and_emails_inactive_users(
    cron_service, mock_email_service, inactive_user
):
    with patch.object(
        cron_service,
        "_find_inactive_trial_users",
        return_value=[inactive_user],
    ):
        with patch.object(
            cron_service,
            "_find_expiring_trials",
            return_value=[],
        ):
            with patch.object(
                cron_service,
                "_has_recent_email",
                return_value=False,
            ):
                with patch.object(
                    cron_service,
                    "_log_email",
                    new_callable=AsyncMock,
                ):
                    await cron_service.check_and_send_emails()

                    mock_email_service.send_reengagement_email.assert_called_once()


@pytest.mark.asyncio
async def test_skips_if_recent_email_sent(
    cron_service, mock_email_service, inactive_user
):
    with patch.object(
        cron_service,
        "_find_inactive_trial_users",
        return_value=[inactive_user],
    ):
        with patch.object(
            cron_service,
            "_find_expiring_trials",
            return_value=[],
        ):
            with patch.object(
                cron_service,
                "_has_recent_email",
                return_value=True,
            ):
                await cron_service.check_and_send_emails()

                mock_email_service.send_reengagement_email.assert_not_called()
