"""Compatibility re-export for the process observability facade."""

from src.observability import (
    capture_exception,
    capture_message,
    distribution_metric,
    flush_observability,
    gauge_metric,
    get_observability_connector,
    increment_metric,
    log_event,
    reset_observability_connector_for_test,
    set_observability_connector,
    set_observability_connector_for_test,
    set_request_context,
    start_span,
    use_noop_observability,
)
from src.observability import (
    initialize_observability as initialize_configured_observability,
)


def initialize_observability() -> None:
    """Install and initialize the infrastructure observability connector."""
    from src.infra.monitoring.sentry import SentryObservabilityConnector

    set_observability_connector(SentryObservabilityConnector())
    initialize_configured_observability()

__all__ = [
    "capture_exception",
    "capture_message",
    "distribution_metric",
    "flush_observability",
    "gauge_metric",
    "get_observability_connector",
    "increment_metric",
    "initialize_observability",
    "log_event",
    "reset_observability_connector_for_test",
    "set_observability_connector",
    "set_observability_connector_for_test",
    "set_request_context",
    "start_span",
    "use_noop_observability",
]
