"""Tests for ResendEmailAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infra.adapters.resend_email_adapter import ResendEmailAdapter


@pytest.fixture
def mock_settings():
    with patch("src.infra.adapters.resend_email_adapter.get_settings") as mock:
        settings = MagicMock()
        settings.RESEND_API_KEY = "re_test_123"
        settings.EMAIL_FROM = "Nutree <test@nutree.app>"
        settings.EMAIL_ENABLED = True
        mock.return_value = settings
        yield settings


@pytest.mark.asyncio
async def test_send_email_success(mock_settings):
    with patch("src.infra.adapters.resend_email_adapter.resend") as mock_resend:
        mock_resend.Emails.send.return_value = {"id": "msg_123"}

        adapter = ResendEmailAdapter()
        result = await adapter.send_email(
            to="user@example.com",
            subject="Welcome!",
            html_body="<p>Hello</p>",
            tags=["welcome"],
        )

        assert result.success is True
        assert result.message_id == "msg_123"
        mock_resend.Emails.send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_disabled(mock_settings):
    mock_settings.EMAIL_ENABLED = False

    adapter = ResendEmailAdapter()
    result = await adapter.send_email(
        to="user@example.com",
        subject="Welcome!",
        html_body="<p>Hello</p>",
    )

    assert result.success is True
    assert result.message_id == "disabled"


@pytest.mark.asyncio
async def test_send_email_api_error(mock_settings):
    with patch("src.infra.adapters.resend_email_adapter.resend") as mock_resend:
        mock_resend.Emails.send.side_effect = Exception("API error")

        adapter = ResendEmailAdapter()
        result = await adapter.send_email(
            to="user@example.com",
            subject="Welcome!",
            html_body="<p>Hello</p>",
        )

        assert result.success is False
        assert "API error" in result.error


@pytest.mark.asyncio
async def test_send_email_no_api_key(mock_settings):
    mock_settings.RESEND_API_KEY = None

    adapter = ResendEmailAdapter()
    result = await adapter.send_email(
        to="user@example.com",
        subject="Welcome!",
        html_body="<p>Hello</p>",
    )

    assert result.success is False
    assert result.error == "API key not configured"
