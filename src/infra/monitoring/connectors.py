"""Provider-neutral observability connector contracts."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from typing import Any, Protocol

SAFE_CONTEXT_KEYS = frozenset(
    {
        "request_id",
        "method",
        "path",
        "route",
        "status_code",
        "elapsed_ms",
        "environment",
        "release",
        "user_id",
        "component",
        "operation",
        "error_type",
        "row_id",
        "event_id",
        "event_type",
        "attempt_count",
        "status",
        "result",
        "phase",
    }
)


SAFE_TAG_KEYS = frozenset(
    {
        "request_id",
        "method",
        "route",
        "status_code",
        "environment",
        "component",
        "operation",
        "error_type",
        "event_type",
        "status",
        "result",
    }
)


SAFE_VALUE_TYPES = (str, int, float, bool, type(None))


def filter_safe_context(context: dict[str, Any] | None) -> dict[str, Any]:
    """Return only allowlisted scalar observability context."""
    if not context:
        return {}

    safe: dict[str, Any] = {}
    for key, value in context.items():
        if key not in SAFE_CONTEXT_KEYS:
            continue
        if isinstance(value, SAFE_VALUE_TYPES):
            safe[key] = value
    return safe


def filter_safe_tags(context: dict[str, Any] | None) -> dict[str, str]:
    """Return allowlisted values that are suitable as provider tags."""
    safe_context = filter_safe_context(context)
    return {
        key: str(value)
        for key, value in safe_context.items()
        if key in SAFE_TAG_KEYS and value is not None
    }


def filter_safe_attributes(attributes: dict[str, Any] | None) -> dict[str, Any]:
    """Return allowlisted scalar attributes for logs and metrics."""
    safe_context = filter_safe_context(attributes)
    return {key: value for key, value in safe_context.items() if value is not None}


class ObservabilityConnector(Protocol):
    """Connector API used by application entry points and infrastructure code."""

    def initialize(self) -> None:
        """Initialize the underlying provider if enabled."""

    def capture_exception(
        self,
        error: BaseException,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Capture an unexpected exception that would otherwise be swallowed."""

    def capture_message(
        self,
        message: str,
        *,
        level: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Capture an operational message."""

    def log_event(
        self,
        level: str,
        message: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Emit a structured operational log."""

    def increment_metric(
        self,
        name: str,
        value: float = 1.0,
        *,
        unit: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Increment an operational counter metric."""

    def gauge_metric(
        self,
        name: str,
        value: float,
        *,
        unit: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record an operational gauge metric."""

    def distribution_metric(
        self,
        name: str,
        value: float,
        *,
        unit: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record an operational distribution metric."""

    def set_request_context(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        user_id: str | None = None,
    ) -> None:
        """Attach safe request context for provider-generated events."""

    def start_span(
        self,
        *,
        operation: str,
        description: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AbstractContextManager[Any]:
        """Start a provider span, or no-op when disabled."""

    def flush(self, *, timeout: float = 5) -> None:
        """Flush pending provider events before process exit."""


class NoopObservabilityConnector:
    """Observability connector used when no provider is enabled."""

    def initialize(self) -> None:
        return None

    def capture_exception(
        self,
        error: BaseException,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        return None

    def capture_message(
        self,
        message: str,
        *,
        level: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        return None

    def log_event(
        self,
        level: str,
        message: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        return None

    def increment_metric(
        self,
        name: str,
        value: float = 1.0,
        *,
        unit: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        return None

    def gauge_metric(
        self,
        name: str,
        value: float,
        *,
        unit: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        return None

    def distribution_metric(
        self,
        name: str,
        value: float,
        *,
        unit: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        return None

    def set_request_context(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        user_id: str | None = None,
    ) -> None:
        return None

    def start_span(
        self,
        *,
        operation: str,
        description: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AbstractContextManager[Any]:
        return nullcontext()

    def flush(self, *, timeout: float = 5) -> None:
        return None
