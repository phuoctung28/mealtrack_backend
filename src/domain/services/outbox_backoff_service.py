"""Exponential backoff computation with jitter for outbox retries."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from src.domain.utils.timezone_utils import ensure_utc, utc_now


def calculate_next_retry_at(
    retry_count: int,
    *,
    now: datetime | None = None,
    base_delay_seconds: float = 5.0,
    max_delay_seconds: float = 3600.0,
    jitter_factor: float = 0.5,
) -> datetime:
    """Calculate the next retry timestamp with exponential backoff and jitter.

    Formula:
        next_retry_at = now + min(base * 2^(min(retry_count, 16)) + jitter, max_delay)
    """
    effective_now = ensure_utc(now) if now is not None else utc_now()
    capped_retries = max(0, min(retry_count, 16))
    backoff = base_delay_seconds * (2**capped_retries)

    jitter = random.uniform(0.0, base_delay_seconds * jitter_factor)
    total_delay = min(backoff + jitter, max_delay_seconds)

    return effective_now + timedelta(seconds=total_delay)
