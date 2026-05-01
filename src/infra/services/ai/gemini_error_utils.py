"""
Utilities for detecting and handling Gemini API errors.
"""

try:
    from google.api_core.exceptions import ResourceExhausted
    HAS_GOOGLE_API_CORE = True
except ImportError:
    HAS_GOOGLE_API_CORE = False
    ResourceExhausted = None

RATE_LIMIT_INDICATORS = (
    "429",
    "resource exhausted",
    "resourceexhausted",
    "503",
    "overloaded",
    "quota",
    "rate limit",
    "too many requests",
)


def is_rate_limit_error(error: Exception) -> bool:
    """
    Check if an exception indicates a rate limit or quota error.

    Detects:
    - google.api_core.exceptions.ResourceExhausted
    - HTTP 429 errors wrapped in exceptions
    - HTTP 503 "overloaded" errors
    - Any exception message containing quota/rate limit keywords
    """
    # Check exception type first
    if HAS_GOOGLE_API_CORE and ResourceExhausted is not None:
        if isinstance(error, ResourceExhausted):
            return True

    # Check exception message
    error_str = str(error).lower()
    return any(indicator in error_str for indicator in RATE_LIMIT_INDICATORS)


def get_retry_after_from_error(error: Exception) -> int:
    """
    Extract retry-after value from error, or return default.

    Returns:
        Seconds to wait before retrying (default: 3)
    """
    error_str = str(error).lower()

    # Check for 503 (model overload) - shorter wait
    if "503" in error_str or "overloaded" in error_str:
        return 2

    # Default for rate limits
    return 3
