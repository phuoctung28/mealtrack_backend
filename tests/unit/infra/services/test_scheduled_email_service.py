"""Tests for ScheduledEmailService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.ports.email_service_port import EmailResult
from src.infra.services.scheduled_email_service import ScheduledEmailService


@pytest.fixture
def mock_email_service():
    service = AsyncMock()
    service.send_reengagement_email.return_value = EmailResult(success=True, message_id="msg_1")
    service.send_trial_expiring_email.return_value = EmailResult(success=True, message_id="msg_2")
    return service


@pytest.fixture
def scheduled_service(mock_email_service):
    return ScheduledEmailService(email_service=mock_email_service)


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
async def test_finds_and_emails_inactive_users(scheduled_service, mock_email_service, inactive_user):
    with patch.object(
        scheduled_service,
        "_find_inactive_trial_users",
        return_value=[inactive_user],
    ):
        with patch.object(
            scheduled_service,
            "_find_expiring_trials",
            return_value=[],
        ):
            with patch.object(
                scheduled_service,
                "_has_recent_email",
                return_value=False,
            ):
                with patch.object(
                    scheduled_service,
                    "_log_email",
                    new_callable=AsyncMock,
                ):
                    await scheduled_service.check_and_send_emails()

                    mock_email_service.send_reengagement_email.assert_called_once()


@pytest.mark.asyncio
async def test_skips_if_recent_email_sent(scheduled_service, mock_email_service, inactive_user):
    with patch.object(
        scheduled_service,
        "_find_inactive_trial_users",
        return_value=[inactive_user],
    ):
        with patch.object(
            scheduled_service,
            "_find_expiring_trials",
            return_value=[],
        ):
            with patch.object(
                scheduled_service,
                "_has_recent_email",
                return_value=True,
            ):
                await scheduled_service.check_and_send_emails()

                mock_email_service.send_reengagement_email.assert_not_called()
