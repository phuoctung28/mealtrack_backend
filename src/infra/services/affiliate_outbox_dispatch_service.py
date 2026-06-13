"""Claims pending outbox rows and delivers them to nutree-affiliate."""

import logging
from typing import cast

from src.infra.adapters.affiliate_service_adapter import AffiliateServiceAdapter
from src.infra.database.config_async import AsyncSessionLocal
from src.infra.monitoring import capture_message, start_span
from src.infra.repositories.affiliate_event_outbox_repository import (
    AffiliateEventOutboxRepository,
)

logger = logging.getLogger(__name__)


async def dispatch_affiliate_outbox(batch_size: int = 50) -> dict:
    """Claim and dispatch one batch of pending affiliate outbox rows.

    Returns a summary dict suitable for cron logging.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Async DB not initialised")

    sent = failed = permanently_failed = skipped = 0
    adapter = AffiliateServiceAdapter()

    with start_span(
        operation="affiliate_outbox.claim",
        description="claim pending affiliate outbox rows",
        context={"component": "affiliate_outbox", "operation": "claim"},
    ):
        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = AffiliateEventOutboxRepository(session)
                rows = await repo.claim_pending(limit=batch_size)

    for row in rows:
        payload = dict(row.payload)
        payload.setdefault("event_id", row.event_id)
        payload.setdefault("event_type", row.event_type)

        try:
            ok = await adapter.send_event(payload)
        except Exception as exc:
            ok = False
            logger.warning("Outbox dispatch exception row=%s: %s", row.id, exc)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                repo = AffiliateEventOutboxRepository(session)
                if ok:
                    await repo.mark_sent(cast(str, row.id))
                    sent += 1
                else:
                    row_id = cast(str, row.id)
                    event_id = cast(str, row.event_id)
                    event_type = cast(str, row.event_type)
                    is_terminal = await repo.mark_failed(
                        row_id, "send_event returned False"
                    )
                    failed += 1
                    if is_terminal:
                        permanently_failed += 1
                        capture_message(
                            "Affiliate outbox row permanently failed",
                            level="error",
                            context={
                                "component": "affiliate_outbox",
                                "operation": "send_event",
                                "row_id": row_id,
                                "event_type": event_type,
                                "event_id": event_id,
                            },
                        )

    logger.info(
        "Affiliate outbox dispatch: sent=%d failed=%d permanently_failed=%d skipped=%d",
        sent,
        failed,
        permanently_failed,
        skipped,
    )
    return {
        "sent": sent,
        "failed": failed,
        "permanently_failed": permanently_failed,
        "skipped": skipped,
    }
