"""Domain model re-export for outbox_status."""

from src.domain.models.outbox_status import OutboxEvent, OutboxStatus

__all__ = ["OutboxEvent", "OutboxStatus"]
