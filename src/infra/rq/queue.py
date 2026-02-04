"""RQ queue factory."""

from __future__ import annotations

from functools import lru_cache

from rq import Queue

from src.infra.rq.redis_connection import get_rq_redis_connection


@lru_cache
def get_queue(name: str = "default") -> Queue:
    """Get a singleton RQ queue."""
    return Queue(name, connection=get_rq_redis_connection())

