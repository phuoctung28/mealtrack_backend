"""Process-wide provider-neutral observability facade."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from src.observability_connectors import (
    NoopObservabilityConnector,
    ObservabilityConnector,
)

_connector: ObservabilityConnector = NoopObservabilityConnector()

# This facade is the application's privacy boundary.  These fields are bounded,
# operational classifications only; identifiers and arbitrary values fail closed.
_SAFE_FIELDS = frozenset(
    {
        "request_id",
        "method",
        "path",
        "route",
        "action",
        "stage",
        "outcome",
        "version",
        "status_code",
        "status",
        "component",
        "operation",
        "error_type",
        "error_code",
        "event_type",
        "provider",
        "ai_provider",
        "ai_model",
        "ai_purpose",
        "ai_stage",
        "failure_kind",
        "cache_hit",
        "attempt_count",
        "attempt_index",
        "elapsed_ms",
        "duration_ms",
        "content_len_bucket",
    }
)
_SAFE_VALUE_TYPES = (str, int, float, bool)


def _safe_fields(values: dict[str, Any] | None) -> dict[str, Any]:
    """Drop non-allowlisted, complex, and potentially identifying telemetry."""
    if not values:
        return {}
    return {
        key: value
        for key, value in values.items()
        if key in _SAFE_FIELDS and isinstance(value, _SAFE_VALUE_TYPES)
    }


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
    safe_context = _safe_fields(context)
    safe_context["error_type"] = type(error).__name__
    get_observability_connector().capture_exception(error, context=safe_context)


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
        context=_safe_fields(context),
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
        attributes=_safe_fields(attributes),
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
        attributes=_safe_fields(attributes),
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
        attributes=_safe_fields(attributes),
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
        attributes=_safe_fields(attributes),
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
        context=_safe_fields(context) if context else None,
    )


def flush_observability(*, timeout: float = 5) -> None:
    """Flush pending provider events before process exit."""
    get_observability_connector().flush(timeout=timeout)


def use_noop_observability() -> None:
    """Install the no-op connector."""
    set_observability_connector(NoopObservabilityConnector())
