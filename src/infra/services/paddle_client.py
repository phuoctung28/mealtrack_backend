"""Server-side Paddle SDK helpers."""

import os


def get_paddle_environment():
    """Resolve Paddle environment from env without a silent default."""
    raw_environment = os.getenv("PADDLE_ENVIRONMENT")
    if not raw_environment:
        raise RuntimeError("PADDLE_ENVIRONMENT must be set to 'production' or 'sandbox'")

    from paddle_billing.Environment import Environment

    normalized = raw_environment.strip().lower()
    if normalized in {"production", "live"}:
        return Environment.PRODUCTION
    if normalized == "sandbox":
        return Environment.SANDBOX
    raise RuntimeError("PADDLE_ENVIRONMENT must be 'production', 'live', or 'sandbox'")


def get_paddle_api_key() -> str:
    """Read Paddle API key from env."""
    api_key = os.getenv("PADDLE_API_KEY") or os.getenv("PADDLE_LIVE_API_KEY")
    if not api_key:
        raise RuntimeError("PADDLE_API_KEY must be set")
    return api_key


def is_paddle_sandbox() -> bool:
    """Return whether the configured Paddle SDK target is the sandbox."""
    from paddle_billing.Environment import Environment

    return get_paddle_environment() == Environment.SANDBOX


def build_paddle_client():
    """Build the Paddle SDK client for server-side API calls."""
    from paddle_billing import Client, Options

    return Client(get_paddle_api_key(), options=Options(get_paddle_environment()))
