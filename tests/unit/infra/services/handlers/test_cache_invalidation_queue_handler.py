from unittest.mock import AsyncMock

import pytest

from src.domain.ports.outbox_handler_port import OutboxEventContext
from src.infra.adapters.cloudflare_queue_publisher import (
    CloudflareQueuePermanentError,
    CloudflareQueueTransientError,
)
from src.infra.services.handlers.cache_invalidation_queue_handler import (
    CacheInvalidationQueueHandler,
)


def _context() -> OutboxEventContext:
    return OutboxEventContext(
        outbox_id="outbox-1",
        event_id="event-1",
        event_type="cache_invalidation.v1",
        retry_count=0,
        created_at_iso="2026-08-22T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_successful_publish_completes_outbox_handler() -> None:
    publisher = AsyncMock()
    result = await CacheInvalidationQueueHandler(publisher).handle(
        {"event_id": "event-1"},
        _context(),
    )

    assert result.success is True
    publisher.publish.assert_awaited_once_with({"event_id": "event-1"})


@pytest.mark.asyncio
async def test_transient_publish_failure_is_retryable() -> None:
    publisher = AsyncMock()
    publisher.publish.side_effect = CloudflareQueueTransientError("timeout")

    result = await CacheInvalidationQueueHandler(publisher).handle({}, _context())

    assert result.success is False
    assert result.is_transient is True


@pytest.mark.asyncio
async def test_permanent_publish_failure_goes_to_outbox_dlq() -> None:
    publisher = AsyncMock()
    publisher.publish.side_effect = CloudflareQueuePermanentError("rejected")

    result = await CacheInvalidationQueueHandler(publisher).handle({}, _context())

    assert result.success is False
    assert result.is_transient is False
