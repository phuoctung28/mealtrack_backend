from unittest.mock import AsyncMock

import httpx
import pytest

from src.infra.adapters.cloudflare_queue_publisher import (
    CloudflareQueueConfigurationError,
    CloudflareQueuePermanentError,
    CloudflareQueuePublisher,
    CloudflareQueueTransientError,
)


def _publisher(client: AsyncMock) -> CloudflareQueuePublisher:
    return CloudflareQueuePublisher(
        account_id="account",
        queue_name="cache-events",
        api_token="queue-token",
        client=client,
    )


@pytest.mark.asyncio
async def test_publish_accepts_cloudflare_success_response() -> None:
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={"success": True})

    await _publisher(client).publish({"event_id": "event-1"})

    client.post.assert_awaited_once()
    request = client.post.call_args.kwargs
    assert request["json"] == {"body": {"event_id": "event-1"}}
    assert request["headers"]["Authorization"] == "Bearer queue-token"


@pytest.mark.asyncio
async def test_publish_retries_rate_limit_and_server_errors() -> None:
    client = AsyncMock()
    client.post.return_value = httpx.Response(503)

    with pytest.raises(CloudflareQueueTransientError):
        await _publisher(client).publish({"event_id": "event-1"})


@pytest.mark.asyncio
async def test_publish_retries_request_timeout_status() -> None:
    client = AsyncMock()
    client.post.return_value = httpx.Response(408)

    with pytest.raises(CloudflareQueueTransientError):
        await _publisher(client).publish({"event_id": "event-1"})


@pytest.mark.asyncio
async def test_publish_retries_unlisted_server_error_status() -> None:
    client = AsyncMock()
    client.post.return_value = httpx.Response(599)

    with pytest.raises(CloudflareQueueTransientError):
        await _publisher(client).publish({"event_id": "event-1"})


@pytest.mark.asyncio
async def test_publish_rejects_invalid_credentials_without_payload_logging() -> None:
    client = AsyncMock()
    client.post.return_value = httpx.Response(403)

    with pytest.raises(CloudflareQueueConfigurationError):
        await _publisher(client).publish({"secret": "must-not-be-logged"})


@pytest.mark.asyncio
async def test_publish_rejects_success_without_confirmation() -> None:
    client = AsyncMock()
    client.post.return_value = httpx.Response(200, json={"success": False})

    with pytest.raises(CloudflareQueuePermanentError):
        await _publisher(client).publish({"event_id": "event-1"})
