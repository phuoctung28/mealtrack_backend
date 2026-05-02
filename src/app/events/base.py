"""
Re-exports from domain layer for backwards compatibility.
"""

from src.domain.events.base import (  # noqa: F401
    Event,
    Command,
    Query,
    DomainEvent,
    EventHandler,
    TEvent,
    TResult,
    handles,
)
