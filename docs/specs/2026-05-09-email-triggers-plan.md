# Email Triggers System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement lifecycle email triggers (welcome, re-engagement, trial expiring, cancellation) using Resend.

**Architecture:** Event-driven email system. WelcomeEmailHandler listens to UserOnboardedEvent. ScheduledEmailService runs daily for re-engagement and trial expiring. RevenueCat webhook triggers cancellation email.

**Tech Stack:** Resend SDK, Jinja2 templates, PyMediator events, Alembic migrations

---

## Task 1: Add Resend dependency and configuration

**Files:**
- Modify: `requirements.txt`
- Modify: `src/infra/config/settings.py`

- [ ] **Step 1: Add resend to requirements.txt**

Add to `requirements.txt`:
```
resend>=2.0.0
```

- [ ] **Step 2: Add Resend settings**

In `src/infra/config/settings.py`, add after the Firebase section (~line 60):

```python
    # Email (Resend)
    RESEND_API_KEY: str | None = Field(default=None)
    EMAIL_FROM: str = Field(default="Nutree <hello@nutree.app>")
    EMAIL_ENABLED: bool = Field(default=False)
```

- [ ] **Step 3: Install dependency**

Run: `pip install resend>=2.0.0`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt src/infra/config/settings.py
git commit -m "chore: add Resend email dependency and config"
```

---

## Task 2: Create EmailLog model and database migration

**Files:**
- Create: `src/infra/database/models/email_log.py`
- Modify: `src/infra/database/models/__init__.py`
- Modify: `src/infra/database/models/user/user.py`
- Create: `alembic/versions/2026_05_09_add_email_fields.py`

- [ ] **Step 1: Create EmailLog model**

Create `src/infra/database/models/email_log.py`:

```python
"""Email log model for tracking sent emails."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.domain.utils.timezone_utils import utc_now
from src.infra.database.config import Base


class EmailLog(Base):
    """Tracks all sent emails for duplicate prevention and debugging."""

    __tablename__ = "email_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email_type = Column(String(50), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resend_message_id = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="sent")

    user = relationship("User", back_populates="email_logs")

    __table_args__ = (
        Index("idx_email_logs_user_type", "user_id", "email_type"),
        Index("idx_email_logs_sent_at", "sent_at"),
    )
```

- [ ] **Step 2: Add email fields to User model**

In `src/infra/database/models/user/user.py`, add after `language_code` (~line 49):

```python
    # Email preferences
    welcome_email_sent_at = Column(DateTime(timezone=True), nullable=True)
    email_opt_out = Column(Boolean, default=False, nullable=False)
```

Add to imports at top:
```python
from sqlalchemy import Column, String, Boolean, DateTime, Text, Index, Enum
```

Add relationship after `referral_wallet` (~line 72):
```python
    email_logs = relationship(
        "EmailLog", back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )
```

- [ ] **Step 3: Export EmailLog in models/__init__.py**

In `src/infra/database/models/__init__.py`, add:

```python
from .email_log import EmailLog
```

And add `"EmailLog"` to `__all__` list.

- [ ] **Step 4: Create migration**

Run: `alembic revision --autogenerate -m "add_email_fields_and_logs"`

- [ ] **Step 5: Verify and edit migration**

Check the generated migration file. It should include:
- Add `welcome_email_sent_at` and `email_opt_out` to `users` table
- Create `email_logs` table with indexes

- [ ] **Step 6: Apply migration**

Run: `alembic upgrade head`

- [ ] **Step 7: Commit**

```bash
git add src/infra/database/models/ alembic/versions/
git commit -m "feat: add email_logs table and user email fields"
```

---

## Task 3: Create EmailServicePort interface

**Files:**
- Create: `src/domain/ports/email_service_port.py`
- Test: `tests/unit/domain/ports/test_email_service_port.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/domain/ports/test_email_service_port.py`:

```python
"""Tests for EmailServicePort interface."""

from dataclasses import dataclass

import pytest

from src.domain.ports.email_service_port import EmailServicePort, EmailResult


@dataclass
class MockEmailAdapter(EmailServicePort):
    """Mock implementation for testing."""

    should_succeed: bool = True

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/ports/test_email_service_port.py -v`
Expected: FAIL with "No module named 'src.domain.ports.email_service_port'"

- [ ] **Step 3: Create the port interface**

Create `src/domain/ports/email_service_port.py`:

```python
"""Port interface for email sending."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailResult:
    """Result of an email send operation."""

    success: bool
    message_id: str | None = None
    error: str | None = None


class EmailServicePort(ABC):
    """Abstract interface for email sending."""

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        tags: list[str] | None = None,
    ) -> EmailResult:
        """Send an email.

        Args:
            to: Recipient email address
            subject: Email subject line
            html_body: HTML content of the email
            tags: Optional tags for tracking

        Returns:
            EmailResult with success status and message_id or error
        """
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/ports/test_email_service_port.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/ports/email_service_port.py tests/unit/domain/ports/test_email_service_port.py
git commit -m "feat: add EmailServicePort interface"
```

---

## Task 4: Create ResendEmailAdapter

**Files:**
- Create: `src/infra/adapters/resend_email_adapter.py`
- Test: `tests/unit/infra/adapters/test_resend_email_adapter.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/infra/adapters/test_resend_email_adapter.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infra/adapters/test_resend_email_adapter.py -v`
Expected: FAIL with "No module named 'src.infra.adapters.resend_email_adapter'"

- [ ] **Step 3: Create the adapter**

Create `src/infra/adapters/resend_email_adapter.py`:

```python
"""Resend email adapter implementation."""

import asyncio
import logging

import resend

from src.domain.ports.email_service_port import EmailResult, EmailServicePort
from src.infra.config.settings import get_settings

logger = logging.getLogger(__name__)


class ResendEmailAdapter(EmailServicePort):
    """Resend SDK wrapper for sending emails."""

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.RESEND_API_KEY
        self._from_email = settings.EMAIL_FROM
        self._enabled = settings.EMAIL_ENABLED

        if self._api_key:
            resend.api_key = self._api_key

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        tags: list[str] | None = None,
    ) -> EmailResult:
        """Send email via Resend API."""
        if not self._enabled:
            logger.info(f"Email disabled, skipping send to {to}: {subject}")
            return EmailResult(success=True, message_id="disabled")

        if not self._api_key:
            logger.warning("RESEND_API_KEY not configured")
            return EmailResult(success=False, error="API key not configured")

        try:
            result = await asyncio.to_thread(
                resend.Emails.send,
                {
                    "from": self._from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                    "tags": [{"name": tag, "value": "true"} for tag in (tags or [])],
                },
            )
            message_id = result.get("id") if isinstance(result, dict) else str(result)
            logger.info(f"Email sent to {to}: {subject} (id={message_id})")
            return EmailResult(success=True, message_id=message_id)

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return EmailResult(success=False, error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infra/adapters/test_resend_email_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/adapters/resend_email_adapter.py tests/unit/infra/adapters/test_resend_email_adapter.py
git commit -m "feat: add ResendEmailAdapter"
```

---

## Task 5: Create email templates

**Files:**
- Create: `src/infra/templates/emails/base.html`
- Create: `src/infra/templates/emails/welcome.html`
- Create: `src/infra/templates/emails/reengagement.html`
- Create: `src/infra/templates/emails/trial_expiring.html`
- Create: `src/infra/templates/emails/trial_cancelled.html`

- [ ] **Step 1: Create templates directory**

Run: `mkdir -p src/infra/templates/emails`

- [ ] **Step 2: Create base template**

Create `src/infra/templates/emails/base.html`:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ subject }}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
    .container { max-width: 600px; margin: 0 auto; background: #fff; }
    .header { background: #22c55e; padding: 30px; text-align: center; }
    .header img { height: 40px; }
    .header h1 { color: #fff; margin: 15px 0 0; font-size: 24px; }
    .content { padding: 40px 30px; }
    .content h2 { color: #22c55e; margin-top: 0; }
    .btn { display: inline-block; background: #22c55e; color: #fff !important; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; margin: 20px 0; }
    .footer { padding: 30px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #eee; }
    .footer a { color: #22c55e; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🌱 Nutree</h1>
    </div>
    <div class="content">
      {% block content %}{% endblock %}
    </div>
    <div class="footer">
      <p>© 2026 Nutree. All rights reserved.</p>
      <p>
        <a href="{{ unsubscribe_url }}">Unsubscribe</a> from these emails
      </p>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 3: Create welcome template**

Create `src/infra/templates/emails/welcome.html`:

```html
{% extends "base.html" %}
{% block content %}
<h2>Your nutrition journey starts now, {{ first_name }}! 🎉</h2>

<p>Welcome to Nutree! You've taken the first step toward understanding your nutrition and reaching your goals.</p>

<p><strong>Your personalized daily target:</strong></p>
<div style="background: #f0fdf4; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
  <div style="font-size: 36px; font-weight: bold; color: #22c55e;">{{ tdee }} kcal</div>
  <div style="color: #666;">Daily calorie target</div>
</div>

<p>Join <strong>10,000+ users</strong> who track their meals daily with Nutree.</p>

<p style="text-align: center;">
  <a href="{{ app_url }}" class="btn">Log Your First Meal</a>
</p>

<p>One meal at a time. You've got this! 💪</p>
{% endblock %}
```

- [ ] **Step 4: Create reengagement template**

Create `src/infra/templates/emails/reengagement.html`:

```html
{% extends "base.html" %}
{% block content %}
<h2>We saved your progress, {{ first_name }} 📊</h2>

<p>We noticed you haven't logged a meal in a few days. Your tracking streak and data are still here, waiting for you.</p>

{% if streak_days > 0 %}
<div style="background: #fef3c7; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
  <div style="font-size: 24px; font-weight: bold; color: #d97706;">{{ streak_days }} day streak</div>
  <div style="color: #666;">Don't let it reset!</div>
</div>
{% endif %}

<p style="text-align: center;">
  <a href="{{ app_url }}" class="btn">Pick Up Where You Left Off</a>
</p>

<p style="color: #666; font-size: 14px;">
  <em>What got in the way? Reply to this email — we read every response.</em>
</p>
{% endblock %}
```

- [ ] **Step 5: Create trial expiring template**

Create `src/infra/templates/emails/trial_expiring.html`:

```html
{% extends "base.html" %}
{% block content %}
<h2>In {{ days_left }} days, your macros go dark ⏰</h2>

<p>Hey {{ first_name }}, your Nutree trial is ending soon.</p>

<p><strong>Here's what you've built so far:</strong></p>
<div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0;">
  <div style="display: flex; justify-content: space-around; text-align: center;">
    <div>
      <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{{ meals_logged }}</div>
      <div style="color: #666; font-size: 14px;">Meals logged</div>
    </div>
    <div>
      <div style="font-size: 24px; font-weight: bold; color: #22c55e;">{{ streak_days }}</div>
      <div style="color: #666; font-size: 14px;">Day streak</div>
    </div>
  </div>
</div>

<p>Keep your progress. Upgrade now and continue your journey.</p>

<p style="text-align: center;">
  <a href="{{ upgrade_url }}" class="btn">Upgrade to Premium</a>
</p>
{% endblock %}
```

- [ ] **Step 6: Create trial cancelled template**

Create `src/infra/templates/emails/trial_cancelled.html`:

```html
{% extends "base.html" %}
{% block content %}
<h2>Before you go — one quick question? 🤔</h2>

<p>Hey {{ first_name }}, we're sorry to see you cancel.</p>

<p>We'd love to know what we could do better. What was the main reason?</p>

<div style="margin: 25px 0;">
  <a href="{{ feedback_url }}?reason=too_expensive" style="display: block; padding: 12px; margin: 8px 0; background: #f5f5f5; border-radius: 6px; text-decoration: none; color: #333;">💰 Too expensive</a>
  <a href="{{ feedback_url }}?reason=not_using" style="display: block; padding: 12px; margin: 8px 0; background: #f5f5f5; border-radius: 6px; text-decoration: none; color: #333;">📱 Wasn't using it enough</a>
  <a href="{{ feedback_url }}?reason=missing_features" style="display: block; padding: 12px; margin: 8px 0; background: #f5f5f5; border-radius: 6px; text-decoration: none; color: #333;">🔧 Missing features I need</a>
  <a href="{{ feedback_url }}?reason=other" style="display: block; padding: 12px; margin: 8px 0; background: #f5f5f5; border-radius: 6px; text-decoration: none; color: #333;">💬 Something else</a>
</div>

<p style="color: #666;">
  <strong>Need a break instead?</strong> You can pause your subscription for 30 days instead of cancelling.
  <a href="{{ pause_url }}" style="color: #22c55e;">Pause instead</a>
</p>

<p>The door is always open if you want to come back. 💚</p>
{% endblock %}
```

- [ ] **Step 7: Commit**

```bash
git add src/infra/templates/emails/
git commit -m "feat: add email templates (welcome, reengagement, expiring, cancelled)"
```

---

## Task 6: Create EmailTemplateRenderer

**Files:**
- Create: `src/infra/services/email_template_renderer.py`
- Test: `tests/unit/infra/services/test_email_template_renderer.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/infra/services/test_email_template_renderer.py`:

```python
"""Tests for EmailTemplateRenderer."""

import pytest

from src.infra.services.email_template_renderer import EmailTemplateRenderer


@pytest.fixture
def renderer():
    return EmailTemplateRenderer()


def test_render_welcome_template(renderer):
    html = renderer.render(
        "welcome",
        {
            "subject": "Welcome!",
            "first_name": "Alex",
            "tdee": 2000,
            "app_url": "https://app.nutree.app",
            "unsubscribe_url": "https://app.nutree.app/unsubscribe",
        },
    )

    assert "Alex" in html
    assert "2000 kcal" in html
    assert "Log Your First Meal" in html
    assert "Unsubscribe" in html


def test_render_reengagement_template(renderer):
    html = renderer.render(
        "reengagement",
        {
            "subject": "We miss you",
            "first_name": "Alex",
            "streak_days": 5,
            "app_url": "https://app.nutree.app",
            "unsubscribe_url": "https://app.nutree.app/unsubscribe",
        },
    )

    assert "Alex" in html
    assert "5 day streak" in html
    assert "Pick Up Where You Left Off" in html


def test_render_with_missing_optional_field(renderer):
    html = renderer.render(
        "reengagement",
        {
            "subject": "We miss you",
            "first_name": "Alex",
            "streak_days": 0,
            "app_url": "https://app.nutree.app",
            "unsubscribe_url": "https://app.nutree.app/unsubscribe",
        },
    )

    assert "Alex" in html
    assert "day streak" not in html  # Hidden when streak is 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infra/services/test_email_template_renderer.py -v`
Expected: FAIL with "No module named 'src.infra.services.email_template_renderer'"

- [ ] **Step 3: Create the renderer**

Create `src/infra/services/email_template_renderer.py`:

```python
"""Email template renderer using Jinja2."""

import os

from jinja2 import Environment, FileSystemLoader


class EmailTemplateRenderer:
    """Renders email templates with Jinja2."""

    def __init__(self):
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "templates", "emails"
        )
        self._env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )

    def render(self, template_name: str, context: dict) -> str:
        """Render an email template.

        Args:
            template_name: Name of template without .html extension
            context: Variables to pass to template

        Returns:
            Rendered HTML string
        """
        template = self._env.get_template(f"{template_name}.html")
        return template.render(**context)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infra/services/test_email_template_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/email_template_renderer.py tests/unit/infra/services/test_email_template_renderer.py
git commit -m "feat: add EmailTemplateRenderer with Jinja2"
```

---

## Task 7: Create EmailService

**Files:**
- Create: `src/domain/services/email_service.py`
- Test: `tests/unit/domain/services/test_email_service.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/domain/services/test_email_service.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/services/test_email_service.py -v`
Expected: FAIL with "No module named 'src.domain.services.email_service'"

- [ ] **Step 3: Create EmailService**

Create `src/domain/services/email_service.py`:

```python
"""Email service for sending lifecycle emails."""

import logging

from src.domain.ports.email_service_port import EmailResult, EmailServicePort

logger = logging.getLogger(__name__)

APP_URL = "https://app.nutree.app"
UPGRADE_URL = "https://app.nutree.app/upgrade"
FEEDBACK_URL = "https://app.nutree.app/feedback"
PAUSE_URL = "https://app.nutree.app/pause"


class EmailService:
    """Business logic for sending lifecycle emails."""

    def __init__(self, email_adapter: EmailServicePort, template_renderer):
        self._adapter = email_adapter
        self._renderer = template_renderer

    async def send_welcome_email(self, user, tdee: int) -> EmailResult:
        """Send welcome email after onboarding."""
        subject = f"Your nutrition journey starts now, {user.first_name or 'there'}! 🎉"

        html = self._renderer.render(
            "welcome",
            {
                "subject": subject,
                "first_name": user.first_name or "there",
                "tdee": tdee,
                "app_url": APP_URL,
                "unsubscribe_url": f"{APP_URL}/unsubscribe?user={user.id}",
            },
        )

        return await self._adapter.send_email(
            to=user.email,
            subject=subject,
            html_body=html,
            tags=["welcome", "onboarding"],
        )

    async def send_reengagement_email(
        self, user, days_inactive: int, streak_days: int = 0
    ) -> EmailResult:
        """Send re-engagement email for inactive users."""
        subject = f"We saved your progress, {user.first_name or 'there'} 📊"

        html = self._renderer.render(
            "reengagement",
            {
                "subject": subject,
                "first_name": user.first_name or "there",
                "streak_days": streak_days,
                "app_url": APP_URL,
                "unsubscribe_url": f"{APP_URL}/unsubscribe?user={user.id}",
            },
        )

        return await self._adapter.send_email(
            to=user.email,
            subject=subject,
            html_body=html,
            tags=["reengagement", f"inactive_{days_inactive}d"],
        )

    async def send_trial_expiring_email(
        self, user, days_left: int, meals_logged: int = 0, streak_days: int = 0
    ) -> EmailResult:
        """Send trial expiring reminder."""
        subject = f"In {days_left} days, your macros go dark ⏰"

        html = self._renderer.render(
            "trial_expiring",
            {
                "subject": subject,
                "first_name": user.first_name or "there",
                "days_left": days_left,
                "meals_logged": meals_logged,
                "streak_days": streak_days,
                "upgrade_url": UPGRADE_URL,
                "unsubscribe_url": f"{APP_URL}/unsubscribe?user={user.id}",
            },
        )

        return await self._adapter.send_email(
            to=user.email,
            subject=subject,
            html_body=html,
            tags=["trial_expiring", f"days_left_{days_left}"],
        )

    async def send_cancellation_email(self, user) -> EmailResult:
        """Send cancellation email with feedback request."""
        subject = "Before you go — one quick question? 🤔"

        html = self._renderer.render(
            "trial_cancelled",
            {
                "subject": subject,
                "first_name": user.first_name or "there",
                "feedback_url": FEEDBACK_URL,
                "pause_url": PAUSE_URL,
                "unsubscribe_url": f"{APP_URL}/unsubscribe?user={user.id}",
            },
        )

        return await self._adapter.send_email(
            to=user.email,
            subject=subject,
            html_body=html,
            tags=["cancellation", "churn"],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/services/test_email_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/domain/services/email_service.py tests/unit/domain/services/test_email_service.py
git commit -m "feat: add EmailService with lifecycle email methods"
```

---

## Task 8: Create WelcomeEmailHandler

**Files:**
- Create: `src/app/handlers/event_handlers/welcome_email_handler.py`
- Modify: `src/app/handlers/event_handlers/__init__.py`
- Test: `tests/unit/handlers/event_handlers/test_welcome_email_handler.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/handlers/event_handlers/test_welcome_email_handler.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/handlers/event_handlers/test_welcome_email_handler.py -v`
Expected: FAIL with "No module named 'src.app.handlers.event_handlers.welcome_email_handler'"

- [ ] **Step 3: Create WelcomeEmailHandler**

Create `src/app/handlers/event_handlers/welcome_email_handler.py`:

```python
"""Welcome email handler — sends welcome email on user onboarding."""

import logging
import uuid

from src.app.events.base import EventHandler, handles
from src.app.events.user.user_onboarded_event import UserOnboardedEvent
from src.domain.services.email_service import EmailService
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.email_log import EmailLog
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


@handles(UserOnboardedEvent)
class WelcomeEmailHandler(EventHandler[UserOnboardedEvent, None]):
    """Sends welcome email when user completes onboarding."""

    def __init__(self, email_service: EmailService):
        self._email_service = email_service

    async def handle(self, event: UserOnboardedEvent) -> None:
        async with AsyncUnitOfWork() as uow:
            user = await uow.users.find_by_id(event.user_id)

            if not user:
                logger.warning(f"User not found for welcome email: {event.user_id}")
                return

            # Skip if already sent or opted out
            if user.welcome_email_sent_at:
                logger.debug(f"Welcome email already sent to user {user.id}")
                return

            if user.email_opt_out:
                logger.debug(f"User {user.id} opted out of emails")
                return

            # Send welcome email
            result = await self._email_service.send_welcome_email(
                user, tdee=int(event.tdee)
            )

            if result.success:
                # Mark as sent
                user.welcome_email_sent_at = utc_now()

                # Log the email
                email_log = EmailLog(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    email_type="welcome",
                    sent_at=utc_now(),
                    resend_message_id=result.message_id,
                    status="sent",
                )
                uow.session.add(email_log)
                await uow.commit()

                logger.info(f"Welcome email sent to user {user.id}")
            else:
                logger.error(f"Failed to send welcome email to {user.id}: {result.error}")
```

- [ ] **Step 4: Export handler in __init__.py**

In `src/app/handlers/event_handlers/__init__.py`, add:

```python
from .welcome_email_handler import WelcomeEmailHandler
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/handlers/event_handlers/test_welcome_email_handler.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/app/handlers/event_handlers/welcome_email_handler.py src/app/handlers/event_handlers/__init__.py tests/unit/handlers/event_handlers/test_welcome_email_handler.py
git commit -m "feat: add WelcomeEmailHandler for onboarding event"
```

---

## Task 9: Add cancellation email to RevenueCat webhook

**Files:**
- Modify: `src/api/routes/v1/webhooks.py`
- Test: `tests/unit/api/routes/test_webhooks_cancellation_email.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/api/routes/test_webhooks_cancellation_email.py`:

```python
"""Tests for cancellation email in RevenueCat webhook."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes.v1.webhooks import handle_cancellation
from src.domain.ports.email_service_port import EmailResult


@pytest.fixture
def mock_email_service():
    service = AsyncMock()
    service.send_cancellation_email.return_value = EmailResult(success=True, message_id="msg_123")
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
async def test_cancellation_sends_email(mock_uow, mock_user, mock_email_service):
    event = {"app_user_id": "rc_123", "product_id": "premium_monthly"}

    with patch(
        "src.api.routes.v1.webhooks._get_email_service",
        return_value=mock_email_service,
    ):
        await handle_cancellation(mock_uow, mock_user, event)

        mock_email_service.send_cancellation_email.assert_called_once_with(mock_user)


@pytest.mark.asyncio
async def test_cancellation_skips_email_if_opted_out(mock_uow, mock_user, mock_email_service):
    mock_user.email_opt_out = True
    event = {"app_user_id": "rc_123", "product_id": "premium_monthly"}

    with patch(
        "src.api.routes.v1.webhooks._get_email_service",
        return_value=mock_email_service,
    ):
        await handle_cancellation(mock_uow, mock_user, event)

        mock_email_service.send_cancellation_email.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/api/routes/test_webhooks_cancellation_email.py -v`
Expected: FAIL

- [ ] **Step 3: Modify handle_cancellation in webhooks.py**

In `src/api/routes/v1/webhooks.py`, add import at top:

```python
from src.domain.services.email_service import EmailService
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.infra.services.email_template_renderer import EmailTemplateRenderer
```

Add helper function after imports:

```python
def _get_email_service() -> EmailService:
    """Get email service instance."""
    adapter = ResendEmailAdapter()
    renderer = EmailTemplateRenderer()
    return EmailService(email_adapter=adapter, template_renderer=renderer)
```

Modify `handle_cancellation` function (~line 204):

```python
async def handle_cancellation(uow, user, event):
    """Handle subscription cancellation."""
    subscription = await get_or_create_subscription(uow, user, event)

    if subscription:
        subscription.status = "cancelled"
        subscription.cancelled_at = utc_now()
        subscription.updated_at = utc_now()
        logger.info(f"User {user.id} cancelled subscription (expires {subscription.expires_at})")

    # Send cancellation email
    if not user.email_opt_out:
        try:
            email_service = _get_email_service()
            await email_service.send_cancellation_email(user)
            logger.info(f"Cancellation email sent to user {user.id}")
        except Exception as e:
            logger.error(f"Failed to send cancellation email to {user.id}: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/api/routes/test_webhooks_cancellation_email.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/routes/v1/webhooks.py tests/unit/api/routes/test_webhooks_cancellation_email.py
git commit -m "feat: add cancellation email to RevenueCat webhook"
```

---

## Task 10: Create ScheduledEmailService

**Files:**
- Create: `src/infra/services/scheduled_email_service.py`
- Test: `tests/unit/infra/services/test_scheduled_email_service.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/infra/services/test_scheduled_email_service.py`:

```python
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


@pytest.fixture
def expiring_user():
    user = MagicMock()
    user.id = "user_expiring"
    user.email = "expiring@example.com"
    user.first_name = "Expiring"
    user.email_opt_out = False
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infra/services/test_scheduled_email_service.py -v`
Expected: FAIL

- [ ] **Step 3: Create ScheduledEmailService**

Create `src/infra/services/scheduled_email_service.py`:

```python
"""Scheduled email service for re-engagement and trial expiring emails."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_, text

from src.domain.services.email_service import EmailService
from src.domain.utils.timezone_utils import utc_now
from src.infra.database.models.email_log import EmailLog
from src.infra.database.models.subscription import Subscription
from src.infra.database.models.user.user import User
from src.infra.database.uow_async import AsyncUnitOfWork

logger = logging.getLogger(__name__)


class ScheduledEmailService:
    """Checks for and sends scheduled lifecycle emails."""

    INACTIVITY_THRESHOLD_DAYS = 3
    TRIAL_EXPIRING_DAYS = 2
    DUPLICATE_WINDOW_DAYS = 7

    def __init__(self, email_service: EmailService):
        self._email_service = email_service

    async def check_and_send_emails(self) -> None:
        """Main entry point — check and send all scheduled emails."""
        now = utc_now()
        logger.info("Running scheduled email check")

        # 1. Re-engagement emails (inactive trial users)
        inactive_users = await self._find_inactive_trial_users(now)
        for user in inactive_users:
            if await self._has_recent_email(user.id, "reengagement"):
                continue
            await self._send_reengagement(user)

        # 2. Trial expiring emails
        expiring = await self._find_expiring_trials(now)
        for user, days_left in expiring:
            if await self._has_recent_email(user.id, "trial_expiring"):
                continue
            await self._send_trial_expiring(user, days_left)

        logger.info(
            f"Scheduled email check complete: "
            f"{len(inactive_users)} inactive, {len(expiring)} expiring"
        )

    async def _find_inactive_trial_users(self, now: datetime) -> list:
        """Find trial users inactive for 3+ days."""
        threshold = now - timedelta(days=self.INACTIVITY_THRESHOLD_DAYS)
        trial_window = now - timedelta(days=7)

        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(User)
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        User.is_active == True,
                        User.email_opt_out == False,
                        User.last_accessed < threshold,
                        Subscription.status == "active",
                        Subscription.purchased_at > trial_window,
                    )
                )
            )
            return list(result.scalars().all())

    async def _find_expiring_trials(self, now: datetime) -> list[tuple]:
        """Find trials expiring in 2 days."""
        expiring_before = now + timedelta(days=self.TRIAL_EXPIRING_DAYS)
        expiring_after = now + timedelta(days=self.TRIAL_EXPIRING_DAYS - 1)

        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(User, Subscription)
                .join(Subscription, User.id == Subscription.user_id)
                .where(
                    and_(
                        User.is_active == True,
                        User.email_opt_out == False,
                        Subscription.status == "active",
                        Subscription.expires_at >= expiring_after,
                        Subscription.expires_at < expiring_before,
                    )
                )
            )
            rows = result.all()
            return [(row.User, self.TRIAL_EXPIRING_DAYS) for row in rows]

    async def _has_recent_email(self, user_id: str, email_type: str) -> bool:
        """Check if user received this email type within duplicate window."""
        cutoff = utc_now() - timedelta(days=self.DUPLICATE_WINDOW_DAYS)

        async with AsyncUnitOfWork() as uow:
            result = await uow.session.execute(
                select(EmailLog).where(
                    and_(
                        EmailLog.user_id == user_id,
                        EmailLog.email_type == email_type,
                        EmailLog.sent_at > cutoff,
                    )
                )
            )
            return result.scalars().first() is not None

    async def _send_reengagement(self, user) -> None:
        """Send re-engagement email and log it."""
        result = await self._email_service.send_reengagement_email(
            user, days_inactive=self.INACTIVITY_THRESHOLD_DAYS, streak_days=0
        )

        if result.success:
            await self._log_email(user.id, "reengagement", result.message_id)
            logger.info(f"Re-engagement email sent to user {user.id}")

    async def _send_trial_expiring(self, user, days_left: int) -> None:
        """Send trial expiring email and log it."""
        result = await self._email_service.send_trial_expiring_email(
            user, days_left=days_left, meals_logged=0, streak_days=0
        )

        if result.success:
            await self._log_email(user.id, "trial_expiring", result.message_id)
            logger.info(f"Trial expiring email sent to user {user.id}")

    async def _log_email(self, user_id: str, email_type: str, message_id: str | None) -> None:
        """Log sent email to database."""
        async with AsyncUnitOfWork() as uow:
            email_log = EmailLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                email_type=email_type,
                sent_at=utc_now(),
                resend_message_id=message_id,
                status="sent",
            )
            uow.session.add(email_log)
            await uow.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infra/services/test_scheduled_email_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/infra/services/scheduled_email_service.py tests/unit/infra/services/test_scheduled_email_service.py
git commit -m "feat: add ScheduledEmailService for re-engagement and trial expiring"
```

---

## Task 11: Register scheduled email job in main.py

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Add scheduled email service to lifespan**

In `src/api/main.py`, find the lifespan function and add the scheduled email service.

Add imports near top:

```python
from src.infra.services.scheduled_email_service import ScheduledEmailService
from src.infra.services.email_template_renderer import EmailTemplateRenderer
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.domain.services.email_service import EmailService
```

In the lifespan function, after `scheduled_notification_service.start()`, add:

```python
    # Start scheduled email service
    email_adapter = ResendEmailAdapter()
    email_renderer = EmailTemplateRenderer()
    email_service = EmailService(email_adapter=email_adapter, template_renderer=email_renderer)
    scheduled_email_service = ScheduledEmailService(email_service=email_service)

    # Run email check daily (integrate with existing scheduler or run on startup)
    # For now, run on startup and rely on cron/external scheduler for daily runs
    try:
        await scheduled_email_service.check_and_send_emails()
    except Exception as e:
        logger.error(f"Scheduled email check failed: {e}")
```

- [ ] **Step 2: Test locally**

Run: `uvicorn src.api.main:app --reload`

Check logs for "Running scheduled email check" message.

- [ ] **Step 3: Commit**

```bash
git add src/api/main.py
git commit -m "feat: register ScheduledEmailService in app lifespan"
```

---

## Task 12: Final integration test

**Files:**
- Create: `tests/integration/test_email_flow.py`

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_email_flow.py`:

```python
"""Integration tests for email flow."""

import pytest
from unittest.mock import patch, AsyncMock

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
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_email_flow.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_email_flow.py
git commit -m "test: add email flow integration tests"
```

---

## Task 13: Update .env.example and documentation

**Files:**
- Modify: `.env.example` (if exists)
- Create: `docs/email-triggers.md`

- [ ] **Step 1: Update .env.example**

Add to `.env.example`:

```
# Email (Resend)
RESEND_API_KEY=re_xxxx
EMAIL_FROM=Nutree <hello@nutree.app>
EMAIL_ENABLED=false
```

- [ ] **Step 2: Create documentation**

Create `docs/email-triggers.md`:

```markdown
# Email Triggers

Lifecycle email system using Resend.

## Email Types

| Type | Trigger | Subject |
|------|---------|---------|
| Welcome | UserOnboardedEvent | "Your nutrition journey starts now, {name}!" |
| Re-engagement | 3 days inactive (scheduled) | "We saved your progress, {name}" |
| Trial Expiring | 2 days before expiration (scheduled) | "In 2 days, your macros go dark" |
| Cancellation | RevenueCat webhook | "Before you go — one quick question?" |

## Configuration

```bash
RESEND_API_KEY=re_xxxx      # Get from resend.com
EMAIL_FROM=Nutree <hello@nutree.app>
EMAIL_ENABLED=true          # Set false in dev/test
```

## Testing

Run with EMAIL_ENABLED=false to skip actual sends.

```bash
pytest tests/unit/domain/services/test_email_service.py -v
pytest tests/integration/test_email_flow.py -v
```

## Templates

Templates are in `src/infra/templates/emails/`:
- `base.html` - Shared layout
- `welcome.html` - Welcome email
- `reengagement.html` - Re-engagement
- `trial_expiring.html` - Trial expiring
- `trial_cancelled.html` - Cancellation
```

- [ ] **Step 3: Commit**

```bash
git add .env.example docs/email-triggers.md
git commit -m "docs: add email triggers documentation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add Resend dependency | requirements.txt, settings.py |
| 2 | Database migration | email_log.py, user.py, migration |
| 3 | EmailServicePort | email_service_port.py |
| 4 | ResendEmailAdapter | resend_email_adapter.py |
| 5 | Email templates | 5 HTML files |
| 6 | EmailTemplateRenderer | email_template_renderer.py |
| 7 | EmailService | email_service.py |
| 8 | WelcomeEmailHandler | welcome_email_handler.py |
| 9 | Webhook integration | webhooks.py |
| 10 | ScheduledEmailService | scheduled_email_service.py |
| 11 | Register in main.py | main.py |
| 12 | Integration tests | test_email_flow.py |
| 13 | Documentation | docs, .env.example |
