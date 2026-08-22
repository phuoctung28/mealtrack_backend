"""Domain models package."""

from src.domain.models.outbox_status import OutboxEvent, OutboxStatus

__all__ = ["OutboxEvent", "OutboxStatus"]
