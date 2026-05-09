"""Tests for EmailService."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.ports.email_service_port import EmailResult
from src.domain.services.email_service import EmailService


@pytest.fixture
def mock_adapter():
    adapter = AsyncMock()
    adapter.send_email.return_value = EmailResult(success=True, message_id="msg_123")
    return adapter


@pytest.fixture
def mock_renderer():
    renderer = MagicMock()
    renderer.render.return_value = "<html>Test</html>"
    return renderer


@pytest.fixture
def email_service(mock_adapter, mock_renderer):
    return EmailService(email_adapter=mock_adapter, template_renderer=mock_renderer)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user_123"
    user.email = "test@example.com"
    user.first_name = "Alex"
    return user


@pytest.mark.asyncio
async def test_send_welcome_email(email_service, mock_user, mock_adapter, mock_renderer):
    result = await email_service.send_welcome_email(mock_user, tdee=2000)

    assert result.success is True
    mock_renderer.render.assert_called_once()
    assert mock_renderer.render.call_args[0][0] == "welcome"
    mock_adapter.send_email.assert_called_once()
    call_kwargs = mock_adapter.send_email.call_args[1]
    assert call_kwargs["to"] == "test@example.com"
    assert "Welcome" in call_kwargs["subject"] or "journey" in call_kwargs["subject"]


@pytest.mark.asyncio
async def test_send_reengagement_email(email_service, mock_user, mock_adapter):
    result = await email_service.send_reengagement_email(mock_user, days_inactive=3, streak_days=5)

    assert result.success is True
    mock_adapter.send_email.assert_called_once()


@pytest.mark.asyncio
async def test_send_trial_expiring_email(email_service, mock_user, mock_adapter):
    result = await email_service.send_trial_expiring_email(
        mock_user, days_left=2, meals_logged=15, streak_days=7
    )

    assert result.success is True
    mock_adapter.send_email.assert_called_once()


@pytest.mark.asyncio
async def test_send_cancellation_email(email_service, mock_user, mock_adapter):
    result = await email_service.send_cancellation_email(mock_user)

    assert result.success is True
    mock_adapter.send_email.assert_called_once()
