"""
Simple cache metrics collector.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.domain.services.timezone_utils import utc_now
from typing import Dict


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_requests: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100


class CacheMonitor:
    """In-memory metrics tracker for cache activity."""

    def __init__(self):
        self.metrics = CacheMetrics()
        self.last_reset = utc_now()

    def record_hit(self) -> None:
        self.metrics.hits += 1
        self.metrics.total_requests += 1

    def record_miss(self) -> None:
        self.metrics.misses += 1
        self.metrics.total_requests += 1

    def record_error(self) -> None:
        self.metrics.errors += 1

    def snapshot(self) -> Dict[str, float | int | str]:
        return {
            "hits": self.metrics.hits,
            "misses": self.metrics.misses,
            "errors": self.metrics.errors,
            "total_requests": self.metrics.total_requests,
            "hit_rate": round(self.metrics.hit_rate, 2),
            "since": self.last_reset.isoformat(),
        }

    def reset(self) -> None:
        self.metrics = CacheMetrics()
        self.last_reset = utc_now()

