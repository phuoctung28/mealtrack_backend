"""Wire the observability facade to the infrastructure provider."""

from src.observability import (
    initialize_observability as initialize_configured_observability,
)
from src.observability import set_observability_connector


def initialize_observability() -> None:
    """Install and initialize the infrastructure observability connector."""
    from src.infra.monitoring.sentry import SentryObservabilityConnector

    set_observability_connector(SentryObservabilityConnector())
    initialize_configured_observability()
