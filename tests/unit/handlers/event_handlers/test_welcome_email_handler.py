"""Tests for WelcomeEmailHandler."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.app.events.user.user_onboarded_event import UserOnboardedEvent
from src.app.handlers.event_handlers.welcome_email_handler import WelcomeEmailHandler
from src.domain.ports.email_service_port import EmailResult


@pytest.fixture
def mock_email_service():
    service = AsyncMock()
    service.send_welcome_email.return_value = EmailResult(success=True, message_id="msg_123")
    return service


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = str(uuid4())
    user.email = "test@example.com"
    user.first_name = "Alex"
    user.welcome_email_sent_at = None
    user.email_opt_out = False
    return user


@pytest.fixture
def onboarded_event(mock_user):
    return UserOnboardedEvent(
        aggregate_id=mock_user.id,
        user_id=mock_user.id,
        profile_id=str(uuid4()),
        tdee=2000.0,
        target_calories=1800.0,
    )


@pytest.mark.asyncio
async def test_sends_welcome_email_on_onboarding(mock_email_service, mock_user, onboarded_event):
    with patch("src.app.handlers.event_handlers.welcome_email_handler.AsyncUnitOfWork") as mock_uow:
        mock_uow_instance = AsyncMock()
        mock_uow_instance.users.find_by_id.return_value = mock_user
        mock_uow.return_value.__aenter__.return_value = mock_uow_instance

        handler = WelcomeEmailHandler(email_service=mock_email_service)
        await handler.handle(onboarded_event)

        mock_email_service.send_welcome_email.assert_called_once_with(
            mock_user, tdee=2000
        )


@pytest.mark.asyncio
async def test_skips_if_already_sent(mock_email_service, mock_user, onboarded_event):
    mock_user.welcome_email_sent_at = datetime.now()

    with patch("src.app.handlers.event_handlers.welcome_email_handler.AsyncUnitOfWork") as mock_uow:
        mock_uow_instance = AsyncMock()
        mock_uow_instance.users.find_by_id.return_value = mock_user
        mock_uow.return_value.__aenter__.return_value = mock_uow_instance

        handler = WelcomeEmailHandler(email_service=mock_email_service)
        await handler.handle(onboarded_event)

        mock_email_service.send_welcome_email.assert_not_called()


@pytest.mark.asyncio
async def test_skips_if_opted_out(mock_email_service, mock_user, onboarded_event):
    mock_user.email_opt_out = True

    with patch("src.app.handlers.event_handlers.welcome_email_handler.AsyncUnitOfWork") as mock_uow:
        mock_uow_instance = AsyncMock()
        mock_uow_instance.users.find_by_id.return_value = mock_user
        mock_uow.return_value.__aenter__.return_value = mock_uow_instance

        handler = WelcomeEmailHandler(email_service=mock_email_service)
        await handler.handle(onboarded_event)

        mock_email_service.send_welcome_email.assert_not_called()
