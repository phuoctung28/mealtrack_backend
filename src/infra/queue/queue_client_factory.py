"""
Factory for creating Redis clients used by the job queue.

Resolves provider from settings (upstash | dedicated) and builds
a RedisClient with the appropriate URL. No automatic fallback.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode, urlparse, urlunparse

from src.infra.cache.redis_client import RedisClient
from src.infra.config.settings import settings

logger = logging.getLogger(__name__)

VALID_PROVIDERS = ("upstash", "dedicated")


def _add_ssl_cert_reqs_none(url: str) -> str:
    """Append ssl_cert_reqs=none to URL to avoid CERTIFICATE_VERIFY_FAILED with Upstash."""
    parsed = urlparse(url)
    query = parsed.query
    params = dict(p.split("=", 1) for p in query.split("&") if p) if query else {}
    params["ssl_cert_reqs"] = "none"
    new_query = urlencode(params)
    return urlunparse(parsed._replace(query=new_query))


def create_queue_redis_client() -> RedisClient:
    """
    Build a RedisClient for the job queue based on QUEUE_PROVIDER.

    Returns:
        RedisClient configured for the selected provider.

    Raises:
        ValueError: If provider is invalid or required URL is missing.
    """
    provider = (settings.QUEUE_PROVIDER or "upstash").strip().lower()
    if provider not in VALID_PROVIDERS:
        raise ValueError(
            f"Invalid QUEUE_PROVIDER '{settings.QUEUE_PROVIDER}'. "
            f"Must be one of: {', '.join(VALID_PROVIDERS)}"
        )

    if provider == "upstash":
        url = settings.UPSTASH_REDIS_URL
        if not url or not url.strip():
            raise ValueError(
                "QUEUE_PROVIDER=upstash requires UPSTASH_REDIS_URL to be set. "
                "Add UPSTASH_REDIS_URL to your environment."
            )
        url = url.strip()
        url = _add_ssl_cert_reqs_none(url)
        max_connections = min(10, settings.REDIS_MAX_CONNECTIONS)
        logger.info("Queue using Upstash Redis (URL configured)")
        return RedisClient(redis_url=url, max_connections=max_connections)

    # dedicated
    url = settings.DEDICATED_REDIS_URL
    if url and url.strip():
        url = url.strip()
        logger.info("Queue using dedicated Redis (DEDICATED_REDIS_URL)")
    else:
        url = settings.redis_url
        logger.info("Queue using dedicated Redis (redis_url from REDIS_* vars)")
    return RedisClient(
        redis_url=url,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
