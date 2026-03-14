"""
Domain models for distributed background jobs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class JobStatus(str, Enum):
    """Status values for background jobs."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class JobPayload:
    """
    Canonical payload used for queue producer/consumer communication.
    """

    job_type: str
    user_id: str
    payload: dict[str, Any]
    priority: int = 0
    max_retries: int = 3
    retry_count: int = 0
    job_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

