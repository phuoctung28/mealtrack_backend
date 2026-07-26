"""ASGI request-body limit for the unauthenticated TDEE preview endpoint."""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

PREVIEW_BODY_MAX_BYTES = 8 * 1024
PREVIEW_PATHS = {"/v1/tdee/preview", "/api/v1/tdee/preview"}


class PreviewBodyLimitMiddleware:
    """Reject oversized preview requests before FastAPI parses their JSON body."""

    def __init__(self, app: ASGIApp, max_bytes: int = PREVIEW_BODY_MAX_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._limits_body(scope):
            await self.app(scope, receive, send)
            return

        if self._content_length_exceeds_limit(scope):
            await self._send_too_large(send)
            return

        messages: list[Message] = []
        body_size = 0
        while True:
            message = await receive()
            messages.append(message)

            if message["type"] != "http.request":
                break

            body_size += len(message.get("body", b""))
            if body_size > self.max_bytes:
                await self._send_too_large(send)
                return
            if not message.get("more_body", False):
                break

        async def replay_receive() -> Message:
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    def _limits_body(scope: Scope) -> bool:
        return (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] in PREVIEW_PATHS
        )

    def _content_length_exceeds_limit(self, scope: Scope) -> bool:
        for name, value in scope.get("headers", []):
            if name.lower() != b"content-length":
                continue
            try:
                if int(value) > self.max_bytes:
                    return True
            except ValueError:
                continue
        return False

    @staticmethod
    async def _send_too_large(send: Send) -> None:
        body = json.dumps(
            {"detail": {"code": "request_too_large"}}, separators=(",", ":")
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
