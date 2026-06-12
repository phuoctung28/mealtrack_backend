"""
Affiliate outbox dispatcher cron entry point.

Run manually:  python -m src.cron.affiliate_outbox
Render cron:   */5 * * * *  (every 5 minutes)

Claims pending affiliate_event_outbox rows and POSTs them to nutree-affiliate.
"""
import asyncio
import logging
import os

import sentry_sdk

from src.infra.database.config_async import async_engine
from src.infra.monitoring.sentry import initialize_sentry
from src.infra.services.affiliate_outbox_dispatch_service import (
    dispatch_affiliate_outbox,
)

logger = logging.getLogger(__name__)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    initialize_sentry()

    if os.getenv("AFFILIATE_INTEGRATION_ENABLED", "").lower() not in ("1", "true"):
        logger.info("AFFILIATE_INTEGRATION_ENABLED not set — skipping outbox dispatch")
        return

    try:
        summary = await dispatch_affiliate_outbox()
        logger.info("Outbox dispatch complete: %s", summary)
    except Exception:
        logger.exception("Affiliate outbox dispatch failed")
        sentry_sdk.capture_exception()
        raise
    finally:
        if async_engine:
            await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
