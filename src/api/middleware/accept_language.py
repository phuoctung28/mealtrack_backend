"""
Accept-Language header parsing middleware.
Extracts language preference and stores in request.state for route handlers.
Pure ASGI implementation — does not subclass BaseHTTPMiddleware, so it never
buffers the request or response body.
"""
import logging

from fastapi import Request
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

# Supported languages (ISO 639-1)
SUPPORTED_LANGUAGES = {"en", "vi", "es", "fr", "de", "ja", "zh"}
DEFAULT_LANGUAGE = "es"


class AcceptLanguageMiddleware:
    """
    Pure ASGI middleware for parsing Accept-Language header.

    Stores validated language code in request.state.language
    for access in route handlers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            language = _parse_accept_language(headers)
            scope.setdefault("state", {})
            scope["state"]["language"] = language
        await self.app(scope, receive, send)


def _parse_accept_language(headers: Headers) -> str:
    """
    Parse Accept-Language header and return validated language code.

    Handles formats:
    - 'en'
    - 'en-US'
    - 'en-US,en;q=0.9,vi;q=0.8'
    """
    header = headers.get("Accept-Language", "")

    if not header:
        return DEFAULT_LANGUAGE

    # 'en-US,en;q=0.9' → 'en-US'
    primary = header.split(",")[0].strip()
    # 'en-US;q=0.9' → 'en-US'
    primary = primary.split(";")[0].strip()
    # 'en-US' → 'en'
    language = primary.split("-")[0].lower()

    if language in SUPPORTED_LANGUAGES:
        return language

    logger.debug(
        f"Unsupported language '{language}' from Accept-Language, "
        f"falling back to '{DEFAULT_LANGUAGE}'"
    )
    return DEFAULT_LANGUAGE


def get_request_language(request: Request) -> str:
    """
    Helper to get language from request state.

    Usage in route handlers:
        @router.get("/example")
        def example(request: Request):
            language = get_request_language(request)
    """
    return getattr(request.state, "language", DEFAULT_LANGUAGE)
