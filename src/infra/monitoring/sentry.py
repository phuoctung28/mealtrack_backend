"""Sentry initialization for the MealTrack API."""

import logging

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
except ModuleNotFoundError:  # pragma: no cover
    sentry_sdk = None

from src.infra.config.settings import settings

logger = logging.getLogger(__name__)


def initialize_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN is configured.

    Must be called BEFORE the FastAPI app is instantiated so integrations
    can patch Starlette/FastAPI middleware.
    """
    if sentry_sdk is None:
        logger.info("Sentry disabled (sentry_sdk not installed)")
        return

    if not settings.SENTRY_DSN:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=settings.SENTRY_SEND_PII,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info("Sentry initialized (env=%s)", settings.ENVIRONMENT)
