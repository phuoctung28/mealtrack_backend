import json
from collections.abc import AsyncIterator

import pytest

from src.api.middleware.preview_body_limit import (
    PREVIEW_BODY_MAX_BYTES,
    PreviewBodyLimitMiddleware,
)


async def _receive_messages(messages: list[dict]) -> AsyncIterator[dict]:
    for message in messages:
        yield message


def _preview_scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "method": "POST",
        "path": "/v1/tdee/preview",
        "headers": headers or [],
    }


@pytest.mark.asyncio
async def test_streamed_oversized_preview_body_without_content_length_is_rejected_preparse():
    received = _receive_messages(
        [
            {"type": "http.request", "body": b"a" * 4096, "more_body": True},
            {"type": "http.request", "body": b"b" * 4097, "more_body": False},
        ]
    )
    sent: list[dict] = []
    app_called = False

    async def receive() -> dict:
        return await anext(received)

    async def send(message: dict) -> None:
        sent.append(message)

    async def app(scope, receive, send) -> None:
        nonlocal app_called
        app_called = True

    middleware = PreviewBodyLimitMiddleware(app)
    await middleware(_preview_scope(), receive, send)

    assert app_called is False
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"]) == {"detail": {"code": "request_too_large"}}


@pytest.mark.asyncio
async def test_preview_body_at_limit_is_replayed_to_the_application():
    body = b"a" * PREVIEW_BODY_MAX_BYTES
    received = _receive_messages(
        [{"type": "http.request", "body": body, "more_body": False}]
    )
    sent: list[dict] = []

    async def receive() -> dict:
        return await anext(received)

    async def send(message: dict) -> None:
        sent.append(message)

    async def app(scope, receive, send) -> None:
        message = await receive()
        assert message["body"] == body
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = PreviewBodyLimitMiddleware(app)
    await middleware(_preview_scope(), receive, send)

    assert sent[0]["status"] == 204


@pytest.mark.asyncio
async def test_oversized_content_length_is_rejected_without_receiving_body():
    receive_calls = 0
    sent: list[dict] = []

    async def receive() -> dict:
        nonlocal receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    async def app(scope, receive, send) -> None:
        raise AssertionError("oversized requests must not reach FastAPI")

    middleware = PreviewBodyLimitMiddleware(app)
    await middleware(
        _preview_scope([(b"content-length", str(PREVIEW_BODY_MAX_BYTES + 1).encode())]),
        receive,
        send,
    )

    assert receive_calls == 0
    assert sent[0]["status"] == 413
