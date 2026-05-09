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
