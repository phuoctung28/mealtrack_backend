"""Compose the web-funnel outbox dispatcher outside the API layer."""

from collections.abc import Awaitable, Callable

from src.infra.services.web_funnel_outbox_dispatch_service import (
    dispatch_web_funnel_outbox,
)

WebFunnelOutboxDispatcher = Callable[..., Awaitable[int]]


def get_web_funnel_outbox_dispatcher() -> WebFunnelOutboxDispatcher:
    """Return the infrastructure dispatcher for a verified web-lead event."""
    return dispatch_web_funnel_outbox
