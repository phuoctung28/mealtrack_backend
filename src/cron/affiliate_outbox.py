"""
Affiliate outbox dispatcher cron entry point.

Run manually:  python -m src.cron.affiliate_outbox
Render cron:   */5 * * * *  (every 5 minutes)

Claims pending affiliate_event_outbox rows and POSTs them to nutree-affiliate.
"""

import asyncio
import logging
import os

from src.infra.database.config_async import async_engine
from src.infra.monitoring import (
    capture_exception,
    flush_observability,
    initialize_observability,
    start_span,
)
from src.infra.services.affiliate_outbox_dispatch_service import (
    dispatch_affiliate_outbox,
)

logger = logging.getLogger(__name__)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    initialize_observability()

    if os.getenv("AFFILIATE_INTEGRATION_ENABLED", "").lower() not in ("1", "true"):
        logger.info("AFFILIATE_INTEGRATION_ENABLED not set — skipping outbox dispatch")
        return

    try:
        with start_span(
            operation="cron.affiliate_outbox", description="affiliate outbox dispatch"
        ):
            summary = await dispatch_affiliate_outbox()
        logger.info("Outbox dispatch complete: %s", summary)
    except Exception as exc:
        logger.exception("Affiliate outbox dispatch failed")
        capture_exception(
            exc,
            context={
                "component": "cron.affiliate_outbox",
                "operation": "dispatch",
            },
        )
        raise
    finally:
        if async_engine:
            await async_engine.dispose()
        flush_observability(timeout=5)


if __name__ == "__main__":
    asyncio.run(run())
