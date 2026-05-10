#!/usr/bin/env python3
"""Send a test email to verify templates and deep links."""

import asyncio
import sys
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, "/Users/alexnguyen/Desktop/Nut/mealtrack_backend")

from src.domain.services.email_service import EmailService
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.infra.services.email_template_renderer import EmailTemplateRenderer


@dataclass
class TestUser:
    id: str = "test-user-123"
    email: str = "alex.nguyen@nutreeai.com"
    first_name: str = "Alex"


async def main():
    email_type = sys.argv[1] if len(sys.argv) > 1 else "welcome"

    adapter = ResendEmailAdapter()
    renderer = EmailTemplateRenderer()
    service = EmailService(adapter, renderer)

    user = TestUser()

    print(f"Sending {email_type} email to {user.email}...")

    if email_type == "welcome":
        result = await service.send_welcome_email(user, tdee=2100)
    elif email_type == "reengagement":
        result = await service.send_reengagement_email(user, days_inactive=3, streak_days=5)
    elif email_type == "trial_expiring":
        result = await service.send_trial_expiring_email(user, days_left=2, meals_logged=42, streak_days=7)
    elif email_type == "cancellation":
        result = await service.send_cancellation_email(user)
    else:
        print(f"Unknown email type: {email_type}")
        print("Available: welcome, reengagement, trial_expiring, cancellation")
        return

    if result.success:
        print(f"✅ Email sent! Message ID: {result.message_id}")
    else:
        print(f"❌ Failed to send: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
