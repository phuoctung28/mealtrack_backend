"""Tests for EmailServicePort interface."""

from abc import ABC

import pytest

from src.domain.ports.email_service_port import EmailServicePort, EmailResult


class MockEmailAdapter(EmailServicePort):
    """Mock implementation for testing."""

    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        tags: list[str] | None = None,
    ) -> EmailResult:
        if self.should_succeed:
            return EmailResult(success=True, message_id="mock_123")
        return EmailResult(success=False, error="mock_error")


def test_email_service_port_is_abstract():
    assert issubclass(EmailServicePort, ABC)


def test_email_service_port_cannot_be_instantiated():
    with pytest.raises(TypeError):
        EmailServicePort()


@pytest.mark.asyncio
async def test_email_service_port_success():
    adapter = MockEmailAdapter(should_succeed=True)
    result = await adapter.send_email(
        to="test@example.com",
        subject="Test",
        html_body="<p>Hello</p>",
    )
    assert result.success is True
    assert result.message_id == "mock_123"


@pytest.mark.asyncio
async def test_email_service_port_failure():
    adapter = MockEmailAdapter(should_succeed=False)
    result = await adapter.send_email(
        to="test@example.com",
        subject="Test",
        html_body="<p>Hello</p>",
    )
    assert result.success is False
    assert result.error == "mock_error"
