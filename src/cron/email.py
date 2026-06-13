"""
Email notification cron entry point.

Run manually:  python -m src.cron.email
Render cron schedule:  0 9 * * *  (09:00 UTC = 16:00 ICT / Vietnam)

Sends:
  - Re-engagement emails to trial users inactive 3+ days
  - Trial-expiring emails to users whose trial ends in 2 days
  Dedup: 7-day window prevents re-sending (email_log table).
"""

import asyncio
import logging

from sqlalchemy import text

from src.domain.services.email_service import EmailService
from src.infra.adapters.resend_email_adapter import ResendEmailAdapter
from src.infra.database.config_async import async_engine
from src.infra.monitoring import (
    capture_exception,
    flush_observability,
    initialize_observability,
    start_span,
)
from src.infra.services.cron_lifecycle_email_service import CronLifecycleEmailService
from src.infra.services.email_template_renderer import EmailTemplateRenderer

logger = logging.getLogger(__name__)


async def run() -> None:
    """Check for and send all lifecycle cron emails, then exit."""
    logging.basicConfig(level=logging.INFO)
    initialize_observability()

    # DB warm-up — triggers Neon compute wakeup; abort if unreachable
    try:
        with start_span(
            operation="cron.db_warmup", description="email cron DB warm-up"
        ):
            if async_engine is None:
                raise RuntimeError("Async database engine is not initialized")
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("DB warm-up failed: %s", exc)
        capture_exception(
            exc,
            context={"component": "cron.email", "operation": "db_warmup"},
        )
        flush_observability(timeout=5)
        return

    try:
        with start_span(operation="cron.email", description="lifecycle email cron"):
            email_adapter = ResendEmailAdapter()
            email_renderer = EmailTemplateRenderer()
            email_service = EmailService(
                email_adapter=email_adapter, template_renderer=email_renderer
            )
            lifecycle_email = CronLifecycleEmailService(email_service=email_service)
            await lifecycle_email.check_and_send_emails()
    except Exception as exc:
        logger.exception("Email cron failed")
        capture_exception(
            exc,
            context={"component": "cron.email", "operation": "send_lifecycle_emails"},
        )

    if async_engine is not None:
        await async_engine.dispose()
    flush_observability(timeout=5)


if __name__ == "__main__":
    asyncio.run(run())
