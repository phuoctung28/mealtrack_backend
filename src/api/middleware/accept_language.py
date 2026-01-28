"""
Accept-Language header parsing middleware.
Extracts language preference and stores in request.state for route handlers.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Supported languages (ISO 639-1)
SUPPORTED_LANGUAGES = {"en", "vi", "es", "fr", "de", "ja", "zh"}
DEFAULT_LANGUAGE = "en"


class AcceptLanguageMiddleware(BaseHTTPMiddleware):
    """
    Middleware for parsing Accept-Language header.

    Stores validated language code in request.state.language
    for access in route handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        language = self._parse_accept_language(request)
        request.state.language = language
        return await call_next(request)

    def _parse_accept_language(self, request: Request) -> str:
        """
        Parse Accept-Language header and return validated language code.

        Handles formats:
        - 'en'
        - 'en-US'
        - 'en-US,en;q=0.9,vi;q=0.8'
        """
        header = request.headers.get("Accept-Language", "")

        if not header:
            return DEFAULT_LANGUAGE

        # Split by comma and take first language
        # 'en-US,en;q=0.9' -> 'en-US'
        primary = header.split(",")[0].strip()

        # Remove quality factor if present
        # 'en;q=0.9' -> 'en'
        primary = primary.split(";")[0].strip()

        # Extract language code (ignore region)
        # 'en-US' -> 'en'
        language = primary.split("-")[0].lower()

        # Validate against supported languages
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
