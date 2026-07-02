"""Tests for cancellation email in RevenueCat webhook."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes.v1.webhooks import handle_cancellation
from src.domain.ports.email_service_port import EmailResult
from src.infra.config.settings import settings


@pytest.fixture
def mock_email_service():
    service = AsyncMock()
    service.send_cancellation_email.return_value = EmailResult(
        success=True, message_id="msg_123"
    )
    return service


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user_123"
    user.email = "test@example.com"
    user.first_name = "Alex"
    user.email_opt_out = False
    return user


@pytest.fixture
def mock_uow():
    uow = AsyncMock()
    uow.subscriptions.find_by_revenuecat_id.return_value = MagicMock(
        status="active",
        expires_at=None,
    )
    return uow


@pytest.mark.asyncio
async def test_cancellation_skips_backend_email_by_default(
    mock_uow, mock_user, mock_email_service
):
    event = {"app_user_id": "rc_123", "product_id": "premium_monthly"}

    with patch(
        "src.api.routes.v1.webhooks._get_email_service",
        return_value=mock_email_service,
    ):
        await handle_cancellation(mock_uow, mock_user, event)

        mock_email_service.send_cancellation_email.assert_not_called()


@pytest.mark.asyncio
async def test_cancellation_sends_legacy_backend_email_when_explicitly_enabled(
    mock_uow, mock_user, mock_email_service
):
    event = {"app_user_id": "rc_123", "product_id": "premium_monthly"}

    with (
        patch.object(settings, "CANCELLATION_EMAIL_OWNER", "backend"),
        patch.object(settings, "EMAIL_ENABLED", True),
        patch(
            "src.api.routes.v1.webhooks._get_email_service",
            return_value=mock_email_service,
        ),
    ):
        await handle_cancellation(mock_uow, mock_user, event)

        mock_email_service.send_cancellation_email.assert_called_once_with(mock_user)


@pytest.mark.asyncio
async def test_cancellation_skips_email_if_opted_out(
    mock_uow, mock_user, mock_email_service
):
    mock_user.email_opt_out = True
    event = {"app_user_id": "rc_123", "product_id": "premium_monthly"}

    with (
        patch.object(settings, "CANCELLATION_EMAIL_OWNER", "backend"),
        patch.object(settings, "EMAIL_ENABLED", True),
        patch(
            "src.api.routes.v1.webhooks._get_email_service",
            return_value=mock_email_service,
        ),
    ):
        await handle_cancellation(mock_uow, mock_user, event)

        mock_email_service.send_cancellation_email.assert_not_called()
