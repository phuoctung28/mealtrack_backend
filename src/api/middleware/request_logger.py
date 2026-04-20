"""
Request/Response logging middleware.
Adds request ID tracking and timing for all API calls.
Pure ASGI implementation — does not subclass BaseHTTPMiddleware, so it never
buffers the request or response body.
"""
import logging
import time
import uuid

from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware:
    """
    Pure ASGI middleware for logging all HTTP requests and responses.

    Features:
    - Generates unique request ID for tracing
    - Logs request method, path, and timing
    - Adds X-Request-ID and X-Response-Time headers to responses
    - Logs slow requests (>1s) at WARNING level
    """

    SLOW_REQUEST_THRESHOLD_SECONDS = 1.0

    SKIP_PATHS = {
        "/health",
        "/v1/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(self, app: ASGIApp, log_body: bool = False) -> None:
        self.app = app
        self.log_body = log_body

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        if request.url.path in self.SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:8]
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        start_time = time.time()
        self._log_request(request, request_id)

        response_logged = False

        async def send_with_headers(message: Message) -> None:
            nonlocal response_logged
            if message["type"] == "http.response.start":
                elapsed = time.time() - start_time
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
                headers.append("X-Response-Time", f"{elapsed:.3f}s")
                await send(message)
                # Log after delivery so elapsed reflects actual time-to-first-byte
                self._log_response(request, message["status"], request_id, elapsed)
                response_logged = True
            else:
                await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception as e:
            elapsed = time.time() - start_time
            # Only log [RES-...] if http.response.start was never sent — avoids a
            # duplicate log line when the app raises mid-stream after headers went out.
            if not response_logged:
                self._log_response(request, 500, request_id, elapsed)
            self._log_error(request, request_id, elapsed, e)
            raise

    def _log_request(self, request: Request, request_id: str) -> None:
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)
        user_str = f" user={user_id}" if user_id else ""
        logger.info(
            f"[REQ-{request_id}] {request.method} {request.url.path}"
            f" client={client_ip}{user_str}"
        )

    def _log_response(
        self,
        request: Request,
        status_code: int,
        request_id: str,
        elapsed: float,
    ) -> None:
        log_level = logging.INFO
        if elapsed > self.SLOW_REQUEST_THRESHOLD_SECONDS:
            log_level = logging.WARNING
        if status_code >= 400:
            log_level = logging.WARNING
        if status_code >= 500:
            log_level = logging.ERROR
        logger.log(
            log_level,
            f"[RES-{request_id}] {request.method} {request.url.path}"
            f" status={status_code} elapsed={elapsed:.3f}s",
        )

    def _log_error(
        self,
        request: Request,
        request_id: str,
        elapsed: float,
        error: Exception,
    ) -> None:
        logger.error(
            f"[ERR-{request_id}] {request.method} {request.url.path}"
            f" elapsed={elapsed:.3f}s error={type(error).__name__}: {error}"
        )

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _get_user_id(self, request: Request) -> str | None:
        try:
            return getattr(request.state, "user_id", None)
        except AttributeError:
            return None


def get_request_id(request: Request) -> str | None:
    """
    Get request ID from request state.

    Usage in route handlers:
        @router.get("/example")
        def example(request: Request):
            request_id = get_request_id(request)
    """
    try:
        return getattr(request.state, "request_id", None)
    except AttributeError:
        return None
