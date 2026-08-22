"""Integration tests for email flow."""

import pytest

from src.domain.ports.email_service_port import EmailResult
from src.domain.services.email_service import EmailService
from src.infra.services.email_template_renderer import EmailTemplateRenderer


class MockEmailAdapter:
    """Mock adapter that tracks sent emails."""

    def __init__(self):
        self.sent_emails = []

    async def send_email(self, to, subject, html_body, tags=None):
        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "html_body": html_body,
            "tags": tags,
        })
        return EmailResult(success=True, message_id=f"mock_{len(self.sent_emails)}")


@pytest.fixture
def mock_adapter():
    return MockEmailAdapter()


@pytest.fixture
def email_service(mock_adapter):
    renderer = EmailTemplateRenderer()
    return EmailService(email_adapter=mock_adapter, template_renderer=renderer)


class MockUser:
    def __init__(self):
        self.id = "test_user_123"
        self.email = "test@example.com"
        self.first_name = "Test"


@pytest.mark.asyncio
async def test_welcome_email_renders_correctly(email_service, mock_adapter):
    user = MockUser()

    result = await email_service.send_welcome_email(user, tdee=2000)

    assert result.success is True
    assert len(mock_adapter.sent_emails) == 1

    email = mock_adapter.sent_emails[0]
    assert email["to"] == "test@example.com"
    assert "Test" in email["subject"]
    assert "2000 kcal" in email["html_body"]
    assert "Log Your First Meal" in email["html_body"]


@pytest.mark.asyncio
async def test_all_email_types_render(email_service, mock_adapter):
    user = MockUser()

    await email_service.send_welcome_email(user, tdee=2000)
    await email_service.send_reengagement_email(user, days_inactive=3, streak_days=5)
    await email_service.send_trial_expiring_email(user, days_left=2, meals_logged=10, streak_days=7)
    await email_service.send_cancellation_email(user)

    assert len(mock_adapter.sent_emails) == 4

    # Verify each email has required elements
    for email in mock_adapter.sent_emails:
        assert "Nutree" in email["html_body"]
        assert "Unsubscribe" in email["html_body"]
