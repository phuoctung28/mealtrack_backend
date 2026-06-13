"""Process-wide provider-neutral observability facade."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from src.observability_connectors import (
    NoopObservabilityConnector,
    ObservabilityConnector,
)

_connector: ObservabilityConnector = NoopObservabilityConnector()


def get_observability_connector() -> ObservabilityConnector:
    """Return the process-wide observability connector."""
    return _connector


def set_observability_connector(connector: ObservabilityConnector) -> None:
    """Install the process-wide observability connector."""
    global _connector
    _connector = connector


def set_observability_connector_for_test(
    connector: ObservabilityConnector | None,
) -> None:
    """Replace the process connector in tests."""
    set_observability_connector(connector or NoopObservabilityConnector())


def reset_observability_connector_for_test() -> None:
    """Reset the process connector in tests."""
    use_noop_observability()


def initialize_observability() -> None:
    """Initialize the configured observability provider."""
    get_observability_connector().initialize()


def capture_exception(
    error: BaseException,
    *,
    context: dict[str, Any] | None = None,
) -> None:
    """Capture an unexpected exception through the active connector."""
    get_observability_connector().capture_exception(error, context=context)


def capture_message(
    message: str,
    *,
    level: str = "info",
    context: dict[str, Any] | None = None,
) -> None:
    """Capture an operational message through the active connector."""
    get_observability_connector().capture_message(
        message,
        level=level,
        context=context,
    )


def log_event(
    level: str,
    message: str,
    *,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Emit a structured operational log through the active connector."""
    get_observability_connector().log_event(
        level,
        message,
        attributes=attributes,
    )


def increment_metric(
    name: str,
    value: float = 1.0,
    *,
    unit: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Increment an operational counter metric."""
    get_observability_connector().increment_metric(
        name,
        value,
        unit=unit,
        attributes=attributes,
    )


def gauge_metric(
    name: str,
    value: float,
    *,
    unit: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record an operational gauge metric."""
    get_observability_connector().gauge_metric(
        name,
        value,
        unit=unit,
        attributes=attributes,
    )


def distribution_metric(
    name: str,
    value: float,
    *,
    unit: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record an operational distribution metric."""
    get_observability_connector().distribution_metric(
        name,
        value,
        unit=unit,
        attributes=attributes,
    )


def set_request_context(
    *,
    request_id: str,
    method: str,
    path: str,
    user_id: str | None = None,
) -> None:
    """Attach safe request context to later provider events."""
    get_observability_connector().set_request_context(
        request_id=request_id,
        method=method,
        path=path,
        user_id=user_id,
    )


def start_span(
    *,
    operation: str,
    description: str | None = None,
    context: dict[str, Any] | None = None,
) -> AbstractContextManager[Any]:
    """Start a provider span, or no-op when disabled."""
    return get_observability_connector().start_span(
        operation=operation,
        description=description,
        context=context,
    )


def flush_observability(*, timeout: float = 5) -> None:
    """Flush pending provider events before process exit."""
    get_observability_connector().flush(timeout=timeout)


def use_noop_observability() -> None:
    """Install the no-op connector."""
    set_observability_connector(NoopObservabilityConnector())
