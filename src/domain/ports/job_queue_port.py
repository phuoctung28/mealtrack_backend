"""
Port interface for distributed job queue operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.model.job_queue import JobPayload, JobStatus


class JobQueuePort(ABC):
    """Port interface for queueing and consuming background jobs."""

    @abstractmethod
    async def enqueue(self, payload: JobPayload) -> str:
        """Enqueue a job and return its job_id."""
        pass

    @abstractmethod
    async def dequeue(
        self, job_types: list[str], block_ms: int = 5000
    ) -> Optional[JobPayload]:
        """Consume the next available job."""
        pass

    @abstractmethod
    async def ack(self, job_id: str) -> None:
        """Acknowledge successful processing."""
        pass

    @abstractmethod
    async def nack(self, job_id: str, error: str) -> None:
        """Mark processing failure and trigger retry/DLQ logic."""
        pass

    @abstractmethod
    async def get_status(self, job_id: str) -> Optional[JobStatus]:
        """Return the current status of a job."""
        pass

